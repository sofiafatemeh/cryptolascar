import os
import json
import logging
from datetime import date

import httpx

logger = logging.getLogger(__name__)


def push_report(
    report_type: str,
    report_date: date,
    content_md: str,
    content_html: str | None = None,
    metadata: dict | None = None,
) -> bool:
    vercel_url = os.getenv("VERCEL_INGEST_URL", "").rstrip("/")
    api_key = os.getenv("INGEST_API_KEY", "")
    if not vercel_url or not api_key:
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
            f"{vercel_url}/api/ingest",
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            content=json.dumps(payload),
            timeout=15,
        )
        resp.raise_for_status()
        logger.info("vercel push ok — %s/%s", report_type, report_date)
        return True
    except Exception as e:
        logger.error("vercel push failed — %s: %s", report_type, e)
        return False
