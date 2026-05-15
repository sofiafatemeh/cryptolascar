import os
import json
import logging
from datetime import date

import httpx

logger = logging.getLogger(__name__)

_VERCEL_URL = os.getenv("VERCEL_INGEST_URL", "").rstrip("/")
_API_KEY = os.getenv("INGEST_API_KEY", "")


def push_report(
    report_type: str,
    report_date: date,
    content_md: str,
    content_html: str | None = None,
    metadata: dict | None = None,
) -> bool:
    if not _VERCEL_URL or not _API_KEY:
        logger.warning("VERCEL_INGEST_URL or INGEST_API_KEY not set — skipping push")
        return False

    payload = {
        "type": report_type,
        "date": report_date.isoformat(),
        "content_md": content_md,
        "content_html": content_html,
        "metadata": metadata or {},
    }

    try:
        resp = httpx.post(
            f"{_VERCEL_URL}/api/ingest",
            headers={"x-api-key": _API_KEY, "Content-Type": "application/json"},
            content=json.dumps(payload),
            timeout=15,
        )
        resp.raise_for_status()
        logger.info("vercel push ok — %s/%s", report_type, report_date)
        return True
    except Exception as e:
        logger.error("vercel push failed — %s: %s", report_type, e)
        return False
