import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    """An upstream provider did not return a usable response."""


class WordNotFound(Exception):
    """A dictionary provider has no entry for this word."""


def get_json(
    url: str,
    *,
    params: dict | None = None,
    timeout: float = 5.0,
    retries: int = 1,
    missing_is_not_found: bool = False,
) -> Any:
    attempts = max(0, retries) + 1
    for attempt in range(attempts):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            if (response.status_code == 429 or response.status_code >= 500) and attempt + 1 < attempts:
                time.sleep(min(0.1 * (2**attempt), 0.5))
                continue
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status == 404 and missing_is_not_found:
                raise WordNotFound from exc
            logger.warning(
                "Provider HTTP request failed",
                extra={"url": url, "status_code": status, "attempt": attempt + 1},
            )
            if status is not None and status != 429 and status < 500:
                raise ProviderError("Provider returned an HTTP error") from exc
            if attempt + 1 == attempts:
                raise ProviderError("Provider returned an HTTP error") from exc
        except (requests.RequestException, ValueError) as exc:
            logger.warning(
                "Provider request failed",
                extra={"url": url, "attempt": attempt + 1, "error_type": type(exc).__name__},
            )
            if attempt + 1 == attempts:
                raise ProviderError("Provider request failed") from exc
    raise ProviderError("Provider request failed")
