from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
from pathlib import Path
import re
import time
from typing import Any
from urllib import robotparser
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup
import requests
from requests import Response, Session


START_URL = "https://thuvienphapluat.vn/"
DOMAIN = "thuvienphapluat.vn"
SOURCE = "thuvienphapluat.vn"
ROBOTS_URL = "https://thuvienphapluat.vn/robots.txt"
TERMS_URL = "https://thuvienphapluat.vn/en/viewcontentleft.aspx?key=21"
OPERATING_RULES_URL = "https://thuvienphapluat.vn/page/viewcontentleft.aspx?key=94"

MAX_PAGES = 50
REQUEST_DELAY = 2
REQUEST_TIMEOUT = 20
MAX_RETRIES = 3

USER_AGENT = (
    "K3-Day10-Data-Observability-RawCrawler/1.0 "
    "(educational raw public-page crawl; contact: local-development)"
)

RAW_ROOT = Path("data/raw/thuvienphapluat")
HTML_DIR = RAW_ROOT / "html"
RECORDS_PATH = RAW_ROOT / "records.json"
MANIFEST_PATH = RAW_ROOT / "crawl_manifest.json"

RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
STOP_STATUS_CODES = {401, 403}
BLOCKED_CONTENT_PATTERNS = [
    "captcha",
    "recaptcha",
    "cloudflare ray id",
    "access denied",
    "forbidden",
    "không được phép truy cập",
    "khong duoc phep truy cap",
    "vui lòng đăng nhập",
    "vui long dang nhap",
    "đăng nhập để",
    "dang nhap de",
    "login to",
]
LOGIN_PATH_PATTERNS = [
    "login",
    "dang-nhap",
    "dangky",
    "dang-ky",
    "register",
    "quen-mat-khau",
    "forgot",
    "account",
    "profile",
    "member",
    "tien-ich",
]
CONTENT_PATH_KEYWORDS = [
    "van-ban",
    "phap-luat",
    "chinh-sach",
    "hoi-dap",
    "tu-van",
    "cong-van",
    "du-thao",
    "ban-an",
    "tin-tuc",
    "phaply",
    "phap-luat-doanh-nghiep",
    "vbpl",
    "page",
]
TRACKING_QUERY_PREFIXES = ("utm_",)
TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "msclkid",
    "yclid",
    "zarsrc",
    "mc_cid",
    "mc_eid",
}
SKIPPED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".bmp",
    ".mp4",
    ".mov",
    ".avi",
    ".mp3",
    ".wav",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".eot",
    ".css",
    ".js",
    ".zip",
    ".rar",
    ".7z",
}


@dataclass(frozen=True)
class UrlDecision:
    allowed: bool
    reason: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def is_same_domain(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.netloc.lower() == DOMAIN


def normalize_url(url: str, base_url: str = START_URL) -> str | None:
    absolute = urljoin(base_url, url.strip())
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"}:
        return None

    netloc = parsed.netloc.lower()
    if netloc == f"www.{DOMAIN}":
        netloc = DOMAIN
    if netloc != DOMAIN:
        return None

    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    filtered_query = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered in TRACKING_QUERY_KEYS or lowered.startswith(TRACKING_QUERY_PREFIXES):
            continue
        filtered_query.append((key, value))

    query = urlencode(sorted(filtered_query), doseq=True)
    return urlunparse(("https", DOMAIN, path, "", query, ""))


def looks_like_non_content_file(url: str) -> bool:
    return Path(urlparse(url).path.lower()).suffix in SKIPPED_EXTENSIONS


def looks_like_login_or_private_url(url: str) -> bool:
    lowered = url.lower()
    return any(pattern in lowered for pattern in LOGIN_PATH_PATTERNS)


def looks_like_relevant_content_url(url: str) -> bool:
    parsed = urlparse(url)
    lowered_path = parsed.path.lower()
    if lowered_path in {"", "/"}:
        return True
    if "viewcontentleft.aspx" in lowered_path:
        return True
    return any(keyword in lowered_path for keyword in CONTENT_PATH_KEYWORDS)


def should_visit_url(url: str, robots: robotparser.RobotFileParser) -> UrlDecision:
    if not is_same_domain(url):
        return UrlDecision(False, "different domain")
    if looks_like_non_content_file(url):
        return UrlDecision(False, "non-html asset")
    if looks_like_login_or_private_url(url):
        return UrlDecision(False, "login/private path")
    if not looks_like_relevant_content_url(url):
        return UrlDecision(False, "outside legal content scope")
    if not robots.can_fetch(USER_AGENT, url):
        return UrlDecision(False, "blocked by robots.txt")
    return UrlDecision(True, "allowed")


def has_blocked_content(html: str) -> str | None:
    lowered = html[:25000].lower()
    for pattern in BLOCKED_CONTENT_PATTERNS:
        if pattern in lowered:
            return pattern
    return None


def fetch_with_retry(session: Session, url: str) -> Response:
    last_response: Response | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        response = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        last_response = response
        if response.status_code in STOP_STATUS_CODES:
            return response
        if response.status_code not in RETRY_STATUS_CODES:
            return response
        if attempt < MAX_RETRIES:
            time.sleep(2 ** (attempt - 1))
    if last_response is None:
        raise RuntimeError(f"No response returned for {url}")
    return last_response


def title_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    if soup.title and soup.title.string:
        return " ".join(soup.title.string.split())
    heading = soup.find(["h1", "h2"])
    if heading:
        return " ".join(heading.get_text(" ", strip=True).split())
    return ""


def discover_links(html: str, base_url: str, robots: robotparser.RobotFileParser, logger: logging.Logger) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        normalized = normalize_url(anchor["href"], base_url)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        decision = should_visit_url(normalized, robots)
        if decision.allowed:
            links.append(normalized)
        else:
            logger.info("Skip discovered URL: %s (%s)", normalized, decision.reason)
    return links


def html_filename(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", urlparse(url).path.strip("/")).strip("-").lower()
    if not slug:
        slug = "home"
    return f"{slug[:80]}-{digest}.html"


def existing_successful_urls(records: list[dict[str, Any]]) -> set[str]:
    urls: set[str] = set()
    for record in records:
        if record.get("status_code") == 200 and record.get("url"):
            urls.add(record["url"])
    return urls


def load_robots(logger: logging.Logger) -> tuple[robotparser.RobotFileParser, bool, str | None]:
    robots = robotparser.RobotFileParser()
    robots.set_url(ROBOTS_URL)
    try:
        robots.read()
    except Exception as exc:  # noqa: BLE001 - fail closed for crawl permission.
        logger.error("Cannot read robots.txt: %s", exc)
        return robots, False, str(exc)
    allowed = robots.can_fetch(USER_AGENT, START_URL)
    logger.info("robots.txt start URL allowed: %s", allowed)
    return robots, allowed, None


def check_terms(session: Session, logger: logging.Logger) -> list[str]:
    errors: list[str] = []
    for url in (TERMS_URL, OPERATING_RULES_URL):
        try:
            response = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        except requests.RequestException as exc:
            errors.append(f"Cannot fetch terms/rules page {url}: {exc}")
            continue
        if response.status_code != 200:
            errors.append(f"Terms/rules page {url} returned HTTP {response.status_code}")
            continue
        blocked = has_blocked_content(response.text)
        if blocked:
            errors.append(f"Terms/rules page {url} appears blocked by pattern: {blocked}")
        logger.info("Checked public terms/rules page: %s", url)
        time.sleep(REQUEST_DELAY)
    return errors


def make_session() -> Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi,en;q=0.8",
        }
    )
    return session


def crawl(max_pages: int = MAX_PAGES) -> dict[str, Any]:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger = logging.getLogger(__name__)

    HTML_DIR.mkdir(parents=True, exist_ok=True)
    started_at = utc_now_iso()
    records: list[dict[str, Any]] = load_json(RECORDS_PATH, [])
    completed_urls = existing_successful_urls(records)
    session = make_session()
    errors: list[str] = []

    robots, robots_allowed, robots_error = load_robots(logger)
    if robots_error:
        errors.append(robots_error)

    manifest: dict[str, Any] = {
        "start_url": START_URL,
        "started_at": started_at,
        "finished_at": None,
        "max_pages": max_pages,
        "request_delay_seconds": REQUEST_DELAY,
        "pages_success": 0,
        "pages_failed": 0,
        "pages_skipped": 0,
        "robots_allowed": robots_allowed,
        "errors": errors,
    }

    if not robots_allowed:
        message = "robots.txt does not allow crawling the start URL; stopping."
        logger.error(message)
        manifest["errors"].append(message)
        manifest["finished_at"] = utc_now_iso()
        write_json(MANIFEST_PATH, manifest)
        return manifest

    terms_errors = check_terms(session, logger)
    manifest["errors"].extend(terms_errors)
    if terms_errors:
        message = "Cannot verify public terms/rules pages; stopping."
        logger.error(message)
        manifest["errors"].append(message)
        manifest["finished_at"] = utc_now_iso()
        write_json(MANIFEST_PATH, manifest)
        return manifest

    start_url = normalize_url(START_URL)
    queue: deque[str] = deque([start_url] if start_url else [])
    queued: set[str] = set(queue)
    visited_this_run: set[str] = set()
    discovered_total: set[str] = set(queue)

    while queue and manifest["pages_success"] < max_pages:
        url = queue.popleft()
        if url in visited_this_run:
            manifest["pages_skipped"] += 1
            logger.info("Skip URL: %s (already visited this run)", url)
            continue
        visited_this_run.add(url)

        if url in completed_urls:
            manifest["pages_skipped"] += 1
            logger.info("Skip URL: %s (already saved successfully)", url)
            continue

        decision = should_visit_url(url, robots)
        if not decision.allowed:
            manifest["pages_skipped"] += 1
            logger.info("Skip URL: %s (%s)", url, decision.reason)
            continue

        logger.info("Crawling URL: %s", url)
        try:
            response = fetch_with_retry(session, url)
        except requests.RequestException as exc:
            manifest["pages_failed"] += 1
            error = f"{url}: request failed: {exc}"
            manifest["errors"].append(error)
            logger.warning(error)
            time.sleep(REQUEST_DELAY)
            continue

        status_code = response.status_code
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        final_url = normalize_url(response.url) or response.url

        if status_code in STOP_STATUS_CODES:
            manifest["pages_skipped"] += 1
            logger.warning("Skip URL: %s (HTTP %s, no retry/bypass)", url, status_code)
            time.sleep(REQUEST_DELAY)
            continue
        if status_code != 200:
            manifest["pages_failed"] += 1
            manifest["errors"].append(f"{url}: HTTP {status_code}")
            logger.warning("Failed URL: %s (HTTP %s)", url, status_code)
            time.sleep(REQUEST_DELAY)
            continue
        if "html" not in content_type:
            manifest["pages_skipped"] += 1
            logger.info("Skip URL: %s (content type %s)", url, content_type or "unknown")
            time.sleep(REQUEST_DELAY)
            continue
        if not is_same_domain(final_url):
            manifest["pages_skipped"] += 1
            logger.info("Skip URL: %s (redirected outside domain to %s)", url, response.url)
            time.sleep(REQUEST_DELAY)
            continue

        blocked_pattern = has_blocked_content(response.text)
        if blocked_pattern:
            manifest["pages_skipped"] += 1
            logger.warning("Skip URL: %s (blocked/login/CAPTCHA pattern: %s)", url, blocked_pattern)
            time.sleep(REQUEST_DELAY)
            continue

        links = discover_links(response.text, final_url, robots, logger)
        discovered_total.update(links)
        for link in links:
            if link not in queued and link not in visited_this_run and link not in completed_urls:
                queue.append(link)
                queued.add(link)

        html_path = HTML_DIR / html_filename(url)
        html_path.write_text(response.text, encoding=response.encoding or "utf-8", errors="replace")
        record = {
            "url": url,
            "final_url": final_url,
            "title": title_from_html(response.text),
            "fetched_at": utc_now_iso(),
            "status_code": status_code,
            "content_type": content_type,
            "html_file": str(html_path.as_posix()),
            "discovered_links": links,
            "source": SOURCE,
        }
        records.append(record)
        completed_urls.add(url)
        manifest["pages_success"] += 1
        logger.info("Saved raw HTML: %s", html_path.as_posix())
        write_json(RECORDS_PATH, records)
        time.sleep(REQUEST_DELAY)

    manifest["finished_at"] = utc_now_iso()
    manifest["discovered_urls"] = len(discovered_total)
    write_json(RECORDS_PATH, records)
    write_json(MANIFEST_PATH, manifest)
    logger.info(
        "Finished crawl: success=%s failed=%s skipped=%s discovered=%s",
        manifest["pages_success"],
        manifest["pages_failed"],
        manifest["pages_skipped"],
        manifest["discovered_urls"],
    )
    return manifest


def main() -> None:
    crawl()


if __name__ == "__main__":
    main()
