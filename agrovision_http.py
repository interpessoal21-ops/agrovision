"""Small retry helper for transient upstream API failures."""
from __future__ import annotations

import time
import requests

RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}


def get_with_retries(url, *, params=None, timeout=60, attempts=3, backoff_seconds=1.5):
    """GET an upstream resource, retrying transient HTTP/network failures only."""
    last_error = None
    for attempt in range(attempts):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            if response.status_code in RETRYABLE_STATUS_CODES:
                response.raise_for_status()
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as exc:
            last_error = exc
            status = getattr(getattr(exc, "response", None), "status_code", None)
            retryable = status is None or status in RETRYABLE_STATUS_CODES
            if not retryable or attempt == attempts - 1:
                break
            retry_after = None
            headers = getattr(getattr(exc, "response", None), "headers", {}) or {}
            try:
                retry_after = float(headers.get("Retry-After", ""))
            except (TypeError, ValueError):
                pass
            delay = retry_after if retry_after is not None else backoff_seconds * (2 ** attempt)
            time.sleep(min(max(delay, 0), 20))
    raise RuntimeError(
        f"Upstream GET failed after {attempts} attempt(s): {url}. "
        f"Last error: {last_error}"
    ) from last_error
