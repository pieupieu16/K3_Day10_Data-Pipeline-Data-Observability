from dataclasses import asdict, dataclass
import logging
from pathlib import Path
import re
import time
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_text(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"<[^>]+>", "", text)
    return normalize_whitespace(cleaned)


def _extract_date(item: dict[str, Any], date_fields: list[str]) -> str:
    for field in date_fields:
        date_info = item.get(field)
        if isinstance(date_info, dict):
            date_parts = date_info.get("date-parts")
            if isinstance(date_parts, list) and len(date_parts) > 0 and isinstance(date_parts[0], list):
                parts = date_parts[0]
                if len(parts) >= 3:
                    return f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"
                elif len(parts) == 2:
                    return f"{parts[0]:04d}-{parts[1]:02d}-01"
                elif len(parts) == 1:
                    return f"{parts[0]:04d}-01-01"
    return ""


def parse_crossref_payload(payload: dict[str, Any]) -> list[PaperRecord]:
    """Parse Crossref REST API JSON response payload into a list of PaperRecord objects."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        paper_id = str(item.get("DOI", "")).strip()
        if not paper_id:
            continue

        raw_title = item.get("title", [])
        if isinstance(raw_title, list) and len(raw_title) > 0:
            title_str = str(raw_title[0])
        else:
            title_str = str(raw_title or "")
        title = _clean_text(title_str)
        if not title:
            continue

        raw_abstract = item.get("abstract", "")
        summary = _clean_text(raw_abstract)
        summary = re.sub(r"^(abstract|ABSTRACT)[:\s]*", "", summary).strip()

        raw_authors = item.get("author", [])
        authors: list[str] = []
        if isinstance(raw_authors, list):
            for a in raw_authors:
                if isinstance(a, dict):
                    given = str(a.get("given", "")).strip()
                    family = str(a.get("family", "")).strip()
                    name = str(a.get("name", "")).strip()
                    if given and family:
                        author_name = f"{given} {family}"
                    elif family:
                        author_name = family
                    elif given:
                        author_name = given
                    else:
                        author_name = name
                    if author_name:
                        authors.append(normalize_whitespace(author_name))

        raw_subjects = item.get("subject", [])
        categories: list[str] = []
        if isinstance(raw_subjects, list):
            for s in raw_subjects:
                if isinstance(s, str) and s.strip():
                    categories.append(normalize_whitespace(s))

        primary_category = categories[0] if categories else ""

        published = _extract_date(item, ["published-online", "published-print", "published", "issued", "created"])
        updated = _extract_date(item, ["deposited", "created"]) or published

        abs_url = str(item.get("URL", "")).strip()
        if not abs_url and paper_id:
            abs_url = f"https://doi.org/{paper_id}"

        pdf_url = ""
        raw_links = item.get("link", [])
        if isinstance(raw_links, list):
            for link in raw_links:
                if isinstance(link, dict):
                    content_type = str(link.get("content-type", "")).lower()
                    url_str = str(link.get("URL", "")).strip()
                    if "pdf" in content_type or url_str.endswith(".pdf"):
                        pdf_url = url_str
                        break

        if not pdf_url:
            pdf_url = abs_url

        container_titles = item.get("container-title", [])
        if isinstance(container_titles, list) and len(container_titles) > 0 and container_titles[0]:
            comment = str(container_titles[0]).strip()
        else:
            comment = str(item.get("publisher", "")).strip()

        record = PaperRecord(
            paper_id=paper_id,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=comment,
        )
        records.append(record)

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Call Crossref API with retries, save raw response and parsed records to disk."""
    url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {
        "User-Agent": "DataObservabilityLab/1.0 (mailto:student@example.com)"
    }

    max_retries = 5
    backoff_factor = 1.5
    payload: dict[str, Any] | None = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Fetching Crossref API (attempt {attempt}/{max_retries})...")
            response = requests.get(url, params=params, headers=headers, timeout=20)
            if response.status_code == 200:
                payload = response.json()
                break
            elif response.status_code in (429, 500, 502, 503, 504):
                logger.warning(
                    f"Crossref API returned HTTP {response.status_code}. Retrying in attempt {attempt}/{max_retries}..."
                )
                if attempt == max_retries:
                    response.raise_for_status()
                time.sleep(backoff_factor ** attempt)
            else:
                response.raise_for_status()
        except (requests.RequestException, Exception) as exc:
            logger.warning(f"Request failed with error: {exc}. Attempt {attempt}/{max_retries}")
            if attempt == max_retries:
                raise RuntimeError(f"Failed to fetch data from Crossref API after {max_retries} retries: {exc}") from exc
            time.sleep(backoff_factor ** attempt)

    if payload is None:
        raise RuntimeError("No payload received from Crossref API.")

    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)

    records_payload = [asdict(record) for record in records]
    write_json(settings.paths.raw_records_json, records_payload)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load JSON snapshot of parsed records and convert into list of PaperRecord."""
    raw_data = read_json(path)
    records: list[PaperRecord] = []
    if isinstance(raw_data, list):
        for item in raw_data:
            if isinstance(item, dict):
                records.append(PaperRecord(**item))
    return records

