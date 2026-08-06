from __future__ import annotations

import os

from ingestion.thuvienphapluat_crawler import MAX_PAGES, crawl


def main() -> None:
    max_pages = int(os.getenv("MAX_PAGES", str(MAX_PAGES)))
    crawl(max_pages=max_pages)


if __name__ == "__main__":
    main()
