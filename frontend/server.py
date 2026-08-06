"""Backend nho cho frontend Windows Forms cua lab Day 10.

Chi dung thu vien chuan cua Python: khong them dependency vao pyproject.
Chay:  python frontend/server.py  (mac dinh http://127.0.0.1:8765)
"""

from __future__ import annotations

import argparse
import csv
import json
import mimetypes
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
STATIC = Path(__file__).resolve().parent / "static"

# ---------------------------------------------------------------- artifacts


def _p(*parts: str) -> Path:
    return DATA.joinpath(*parts)


# (stage, key, nhan hien thi, duong dan, nguoi phu trach)
ARTIFACTS: list[tuple[str, str, str, Path, str]] = [
    ("1. Ingestion", "raw_response", "crossref_response.json", _p("raw", "crossref_response.json"), "Quan"),
    ("1. Ingestion", "raw_records", "crossref_records.json", _p("raw", "crossref_records.json"), "Quan"),
    ("2. Cleaning", "clean_csv", "papers_clean.csv", _p("clean", "papers_clean.csv"), "Duong"),
    ("2. Cleaning", "clean_json", "papers_clean.json", _p("clean", "papers_clean.json"), "Duong"),
    ("3. Evaluation set", "test_set", "test_set.json", _p("eval", "test_set.json"), "Duong"),
    ("4. Embedding", "embeddings", "papers_embeddings.json", _p("embeddings", "papers_embeddings.json"), "Tung"),
    ("5. Quality", "freshness", "freshness_report.json", _p("quality", "freshness_report.json"), "Long"),
    ("5. Quality", "phase1_report", "phase1_report.md", _p("reports", "phase1_report.md"), "Long"),
    ("6. Baseline", "baseline_metrics", "baseline_metrics.json", _p("results", "baseline_metrics.json"), "Tung"),
    ("6. Baseline", "baseline_answers", "baseline_answers.json", _p("results", "baseline_answers.json"), "Tung"),
    ("7. Corruption", "corrupted_csv", "papers_clean_corrupted.csv", _p("clean", "papers_clean_corrupted.csv"), "Phuong"),
    ("7. Corruption", "corruption_log", "corruption_log.json", _p("results", "corruption_log.json"), "Phuong"),
    ("7. Corruption", "corrupted_metrics", "corrupted_metrics.json", _p("results", "corrupted_metrics.json"), "Tung"),
    ("8. Repair", "repaired_csv", "papers_clean_repaired.csv", _p("clean", "papers_clean_repaired.csv"), "Phuong"),
    ("8. Repair", "repaired_metrics", "repaired_metrics.json", _p("results", "repaired_metrics.json"), "Tung"),
    ("9. Report", "corruption_report", "corruption_report.md", _p("reports", "corruption_report.md"), "Long"),
]

DATASETS = {
    "clean": _p("clean", "papers_clean.csv"),
    "corrupted": _p("clean", "papers_clean_corrupted.csv"),
    "repaired": _p("clean", "papers_clean_repaired.csv"),
}

METRIC_FILES = {
    "baseline": _p("results", "baseline_metrics.json"),
    "corrupted": _p("results", "corrupted_metrics.json"),
    "repaired": _p("results", "repaired_metrics.json"),
}

ANSWER_FILES = {
    "baseline": _p("results", "baseline_answers.json"),
    "corrupted": _p("results", "corrupted_answers.json"),
    "repaired": _p("results", "repaired_answers.json"),
    "demo": _p("results", "agent_demo_answers.json"),
}

REPORT_FILES = {
    "phase1": _p("reports", "phase1_report.md"),
    "corruption": _p("reports", "corruption_report.md"),
}

PIPELINES = {
    "phase1": ROOT / "script" / "run_phase1.py",
    "corruption": ROOT / "script" / "run_corruption_flow.py",
}


# ---------------------------------------------------------------- helpers


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def read_json_file(path: Path):
    return json.loads(read_text(path))


def stat_of(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "size": 0, "modified": None}
    st = path.stat()
    return {
        "exists": True,
        "size": st.st_size,
        "modified": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
        .astimezone()
        .strftime("%Y-%m-%d %H:%M:%S"),
    }


def read_table(path: Path, limit: int, offset: int) -> dict:
    """Doc CSV (hoac JSON list) thanh columns + rows."""
    if not path.exists():
        return {"exists": False, "columns": [], "rows": [], "total": 0}

    if path.suffix.lower() == ".json":
        payload = read_json_file(path)
        records = payload if isinstance(payload, list) else [payload]
        columns = list(records[0].keys()) if records else []
        rows = [[str(rec.get(c, "")) for c in columns] for rec in records[offset : offset + limit]]
        return {"exists": True, "columns": columns, "rows": rows, "total": len(records)}

    with path.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        reader = csv.reader(fh)
        try:
            columns = next(reader)
        except StopIteration:
            return {"exists": True, "columns": [], "rows": [], "total": 0}
        all_rows = list(reader)
    return {
        "exists": True,
        "columns": columns,
        "rows": all_rows[offset : offset + limit],
        "total": len(all_rows),
    }


def env_summary() -> list[dict]:
    """Doc .env / .env.example va che giau secret."""
    path = ROOT / ".env"
    source = ".env"
    if not path.exists():
        path = ROOT / ".env.example"
        source = ".env.example (chua tao .env)"
    items: list[dict] = []
    if path.exists():
        for line in read_text(path).splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key, value = key.strip(), value.strip()
            if any(tag in key.upper() for tag in ("KEY", "TOKEN", "SECRET")):
                value = ("*" * 8 + value[-4:]) if len(value) > 4 else ("(trong)" if not value else "*" * len(value))
            items.append({"key": key, "value": value})
    return [{"key": "__source__", "value": source}] + items


# ---------------------------------------------------------------- pipeline runner


class Runner:
    """Chay script pipeline trong subprocess, giu log de frontend poll."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.proc: subprocess.Popen | None = None
        self.lines: list[str] = []
        self.pipeline: str | None = None
        self.started_at: str | None = None
        self.exit_code: int | None = None

    @staticmethod
    def python_exe() -> str:
        for name in (".venv", "venv"):
            for candidate in (ROOT / name / "Scripts" / "python.exe", ROOT / name / "bin" / "python"):
                if candidate.exists():
                    return str(candidate)
        return sys.executable

    @staticmethod
    def python_info() -> dict:
        """Kiem tra interpreter se dung co dung 3.11-3.13 khong."""
        exe = Runner.python_exe()
        try:
            out = subprocess.run(
                [exe, "-c", "import sys;print('%d.%d.%d' % sys.version_info[:3])"],
                capture_output=True,
                text=True,
                timeout=20,
            )
            version = out.stdout.strip() or out.stderr.strip()
        except Exception as exc:
            return {"exe": exe, "version": "?", "ok": False, "note": str(exc)}
        parts = version.split(".")
        try:
            major, minor = int(parts[0]), int(parts[1])
        except (IndexError, ValueError):
            return {"exe": exe, "version": version, "ok": False, "note": "Khong doc duoc phien ban."}
        ok = (major, minor) >= (3, 11) and (major, minor) < (3, 14)
        note = "" if ok else "Project yeu cau Python 3.11-3.13. Tao .venv dung phien ban roi chay lai (uv sync hoac python -m venv .venv)."
        venv = next((n for n in (".venv", "venv") if (ROOT / n).exists()), None)
        return {"exe": exe, "version": version, "ok": ok, "note": note, "venv": venv}

    def is_running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self, name: str) -> dict:
        script = PIPELINES.get(name)
        if script is None:
            return {"ok": False, "error": f"Pipeline khong hop le: {name}"}
        if not script.exists():
            return {"ok": False, "error": f"Khong tim thay {script}"}
        with self.lock:
            if self.is_running():
                return {"ok": False, "error": f"Pipeline '{self.pipeline}' dang chay."}
            env = os.environ.copy()
            src = str(ROOT / "src")
            env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUNBUFFERED"] = "1"
            exe = self.python_exe()
            self.lines = [
                f"> {exe} {script.relative_to(ROOT)}",
                f"> cwd = {ROOT}",
                "",
            ]
            self.pipeline = name
            self.exit_code = None
            self.started_at = datetime.now().strftime("%H:%M:%S")
            self.proc = subprocess.Popen(
                [exe, str(script)],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
        threading.Thread(target=self._pump, args=(self.proc,), daemon=True).start()
        return {"ok": True, "pipeline": name}

    def _pump(self, proc: subprocess.Popen) -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            with self.lock:
                self.lines.append(line.rstrip("\n"))
                if len(self.lines) > 5000:
                    del self.lines[: len(self.lines) - 5000]
        code = proc.wait()
        with self.lock:
            self.exit_code = code
            self.lines.append("")
            self.lines.append(f"--- Ket thuc, exit code = {code} ---")

    def stop(self) -> dict:
        with self.lock:
            if not self.is_running():
                return {"ok": False, "error": "Khong co pipeline nao dang chay."}
            self.proc.terminate()  # type: ignore[union-attr]
            self.lines.append("--- Da gui lenh dung (terminate) ---")
        return {"ok": True}

    def state(self, offset: int) -> dict:
        with self.lock:
            offset = max(0, min(offset, len(self.lines)))
            return {
                "running": self.is_running(),
                "pipeline": self.pipeline,
                "started_at": self.started_at,
                "exit_code": self.exit_code,
                "offset": len(self.lines),
                "lines": self.lines[offset:],
            }

    def clear(self) -> dict:
        with self.lock:
            if self.is_running():
                return {"ok": False, "error": "Dang chay, khong the xoa log."}
            self.lines = []
            self.pipeline = None
            self.exit_code = None
        return {"ok": True}


RUNNER = Runner()


# ---------------------------------------------------------------- API


def api_status() -> dict:
    stages: dict[str, list[dict]] = {}
    for stage, key, label, path, owner in ARTIFACTS:
        info = stat_of(path)
        info.update(
            {
                "key": key,
                "label": label,
                "owner": owner,
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            }
        )
        stages.setdefault(stage, []).append(info)
    done = sum(1 for _, _, _, path, _ in ARTIFACTS if path.exists())
    return {
        "project": ROOT.name,
        "root": str(ROOT),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "artifact_done": done,
        "artifact_total": len(ARTIFACTS),
        "stages": [{"stage": stage, "items": items} for stage, items in stages.items()],
    }


def api_metrics() -> dict:
    out: dict[str, dict | None] = {}
    for name, path in METRIC_FILES.items():
        try:
            out[name] = read_json_file(path) if path.exists() else None
        except Exception as exc:  # file dang duoc ghi do
            out[name] = {"error": str(exc)}
    return {"metrics": out, "keys": ["samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]}


def api_quality() -> dict:
    files = []
    quality_dir = DATA / "quality"
    if quality_dir.exists():
        for path in sorted(quality_dir.rglob("*.json")):
            try:
                content = read_json_file(path)
            except Exception as exc:
                content = {"error": str(exc)}
            files.append(
                {
                    "name": str(path.relative_to(quality_dir)).replace("\\", "/"),
                    "content": content,
                    **stat_of(path),
                }
            )
    log_path = _p("results", "corruption_log.json")
    corruption_log = None
    if log_path.exists():
        try:
            corruption_log = read_json_file(log_path)
        except Exception as exc:
            corruption_log = {"error": str(exc)}
    return {"files": files, "corruption_log": corruption_log}


def api_report(name: str) -> dict:
    path = REPORT_FILES.get(name)
    if path is None:
        return {"error": f"Report khong hop le: {name}"}
    if not path.exists():
        return {"exists": False, "path": str(path.relative_to(ROOT)).replace("\\", "/"), "content": ""}
    return {
        "exists": True,
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "content": read_text(path),
        **stat_of(path),
    }


def api_answers(state: str) -> dict:
    path = ANSWER_FILES.get(state)
    if path is None:
        return {"error": f"State khong hop le: {state}"}
    if not path.exists():
        return {"exists": False, "items": []}
    try:
        items = read_json_file(path)
    except Exception as exc:
        return {"exists": True, "items": [], "error": str(exc)}
    return {"exists": True, "items": items if isinstance(items, list) else [items]}


def api_testset() -> dict:
    path = _p("eval", "test_set.json")
    if not path.exists():
        return {"exists": False, "items": []}
    try:
        items = read_json_file(path)
    except Exception as exc:
        return {"exists": True, "items": [], "error": str(exc)}
    return {"exists": True, "items": items if isinstance(items, list) else [items]}


# ---------------------------------------------------------------- HTTP


class Handler(BaseHTTPRequestHandler):
    server_version = "Day10Console/1.0"

    def log_message(self, fmt: str, *args) -> None:  # bot log rac
        if "/api/run" in (args[0] if args else ""):
            return
        sys.stderr.write("  %s\n" % (fmt % args))

    # -- utils
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError):
            pass

    def _json(self, payload, code: int = 200) -> None:
        self._send(code, json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"), "application/json; charset=utf-8")

    def _static(self, rel: str) -> None:
        target = (STATIC / rel).resolve()
        if not str(target).startswith(str(STATIC.resolve())) or not target.is_file():
            self._send(404, b"Not found", "text/plain; charset=utf-8")
            return
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",):
            ctype += "; charset=utf-8"
        self._send(200, target.read_bytes(), ctype)

    # -- routes
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        def qs(name: str, default: str = "") -> str:
            return query.get(name, [default])[0]

        try:
            if path in ("/", "/index.html"):
                self._static("index.html")
            elif path.startswith("/static/"):
                self._static(path[len("/static/") :])
            elif not path.startswith("/api/") and (STATIC / path.lstrip("/")).is_file():
                # cho phep ca duong dan tuong doi kieu ./style.css
                self._static(path.lstrip("/"))
            elif path == "/api/status":
                self._json(api_status())
            elif path == "/api/dataset":
                name = qs("name", "clean")
                target = DATASETS.get(name)
                if target is None:
                    self._json({"error": f"Dataset khong hop le: {name}"}, 400)
                    return
                data = read_table(target, int(qs("limit", "100")), int(qs("offset", "0")))
                data["name"] = name
                data["path"] = str(target.relative_to(ROOT)).replace("\\", "/")
                self._json(data)
            elif path == "/api/metrics":
                self._json(api_metrics())
            elif path == "/api/quality":
                self._json(api_quality())
            elif path == "/api/report":
                self._json(api_report(qs("name", "phase1")))
            elif path == "/api/answers":
                self._json(api_answers(qs("state", "baseline")))
            elif path == "/api/testset":
                self._json(api_testset())
            elif path == "/api/config":
                self._json({"env": env_summary(), "python": Runner.python_info(), "root": str(ROOT)})
            elif path == "/api/run":
                self._json(RUNNER.state(int(qs("offset", "0"))))
            else:
                self._send(404, b"Not found", "text/plain; charset=utf-8")
        except Exception as exc:  # tra loi loi thay vi 500 tran
            self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            body = {}

        if parsed.path == "/api/run":
            self._json(RUNNER.start(str(body.get("pipeline", "phase1"))))
        elif parsed.path == "/api/run/stop":
            self._json(RUNNER.stop())
        elif parsed.path == "/api/run/clear":
            self._json(RUNNER.clear())
        else:
            self._send(404, b"Not found", "text/plain; charset=utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Day 10 Data Pipeline Console (frontend)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true", help="Khong tu mo trinh duyet")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print("=" * 62)
    print("  Day 10 - Data Pipeline & Observability Console")
    print(f"  Project : {ROOT}")
    print(f"  URL     : {url}")
    print("  Ctrl+C de dung server")
    print("=" * 62)
    if not args.no_browser:
        threading.Timer(0.8, lambda: __import__("webbrowser").open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDang dung server...")
        server.shutdown()


if __name__ == "__main__":
    main()
