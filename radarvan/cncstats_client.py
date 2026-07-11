"""Single HTTP client for the cncstats web API.

Every outbound call to ``cncstats.computersrfun.org`` goes through
``CncstatsClient``: replay parsing (``POST /replay``) and the map registry
(``GET /get_map`` / ``POST /add_map``). Get the process-wide instance via the
``cncstats_client()`` factory - it is ``@cache``d so one ``httpx.Client`` is
reused for the lifetime of the process (connection pooling, one place to
configure).

Two distinct credentials are involved and must not be conflated:
  * ``CNCSTATS_APIKEY``  - Bearer token for ``/replay`` parsing.
  * ``CNCSTATS_API_KEY`` - X-API-Key for the ``/add_map`` registry.
"""

from __future__ import annotations

import os
from functools import cache

import httpx
import structlog

logger = structlog.get_logger(__name__)

BASE_URL = "https://cncstats.computersrfun.org"
# Bearer token for replay parsing (POST /replay).
PARSE_BEARER_ENV = "CNCSTATS_APIKEY"
# X-API-Key for the map registry (POST /add_map).
MAP_API_KEY_ENV = "CNCSTATS_API_KEY"

# X-Map-File asset types accepted by /add_map.
ADD_MAP_FILE_MAP = "map"
ADD_MAP_FILE_PREVIEW = "preview"

_PARSE_TIMEOUT = 30.0
_MAP_TIMEOUT = 60.0


class CncstatsClient:
    """Thin wrapper over a shared ``httpx.Client`` for the cncstats API.

    Credentials are sent per-request (the underlying client carries no default
    auth header) so the Bearer parse token never leaks onto map-registry calls.
    """

    def __init__(
        self,
        *,
        base_url: str = BASE_URL,
        parse_token: str | None = None,
        map_api_key: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._parse_token = parse_token
        self._map_api_key = map_api_key
        self._client = client or httpx.Client(timeout=_MAP_TIMEOUT)
        # Created lazily on first async use (and bound to that event loop).
        self._async_client: httpx.AsyncClient | None = None

    def _aclient(self) -> httpx.AsyncClient:
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(timeout=_MAP_TIMEOUT)
        return self._async_client

    # --- replay parsing -------------------------------------------------

    def parse_replay(self, data: bytes) -> httpx.Response:
        """POST a raw replay to ``/replay`` and return the response.

        Does not ``raise_for_status``; the caller validates the JSON body (and
        logs ``response.elapsed`` / headers).
        """
        if not self._parse_token:
            raise RuntimeError(f"{PARSE_BEARER_ENV} is not set; cannot parse replays")
        headers = {"Authorization": f"Bearer {self._parse_token}"}
        return self._client.post(
            f"{self._base_url}/replay",
            files={"file": data},
            headers=headers,
            timeout=_PARSE_TIMEOUT,
        )

    # --- map registry ---------------------------------------------------

    @property
    def map_push_enabled(self) -> bool:
        """True if a map-registry API key is configured (``/add_map`` usable)."""
        return bool(self._map_api_key)

    async def map_exists_async(self, crc_decimal: int) -> bool:
        """GET /map_exists - True if cncstats already stores this map's CRC.

        Plain-text ``"true"``/``"false"``; no auth required.
        """
        resp = await self._aclient().get(
            f"{self._base_url}/map_exists", params={"crc": crc_decimal}
        )
        resp.raise_for_status()
        return resp.text.strip().lower() == "true"

    def get_map_zip(self, crc_decimal: int) -> bytes:
        """Download the cncstats map zip for a CRC (decimal). Raises on HTTP error."""
        resp = self._client.get(
            f"{self._base_url}/get_map",
            params={"crc": crc_decimal},
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.content

    def _add_map_headers(
        self, crc_decimal: int, file_type: str, map_name: str | None
    ) -> dict[str, str]:
        """X-Map-* headers for an /add_map call.

        ``file_type`` is an X-Map-File value (``map``, ``preview``, ``ini``,
        ``str``, ``solo``, ``assets``, ``readme``). cncstats keys assets by
        ``crc_decimal``; an identical CRC overwrites silently.
        """
        if not self._map_api_key:
            raise RuntimeError(f"{MAP_API_KEY_ENV} is not set; cannot push to cncstats")
        headers = {
            "X-API-Key": self._map_api_key,
            "X-Map-CRC": str(crc_decimal),
            "X-Map-File": file_type,
            "Content-Type": "application/octet-stream",
        }
        if map_name:
            headers["X-Map-Name"] = map_name
        return headers

    def add_map(
        self,
        crc_decimal: int,
        file_type: str,
        data: bytes,
        *,
        map_name: str | None = None,
    ) -> None:
        """POST one map asset to ``/add_map`` (raw octet-stream). Raises on error."""
        headers = self._add_map_headers(crc_decimal, file_type, map_name)
        resp = self._client.post(
            f"{self._base_url}/add_map", content=data, headers=headers
        )
        resp.raise_for_status()

    async def add_map_async(
        self,
        crc_decimal: int,
        file_type: str,
        data: bytes,
        *,
        map_name: str | None = None,
    ) -> None:
        """Async variant of `add_map`, for pushing many assets concurrently."""
        headers = self._add_map_headers(crc_decimal, file_type, map_name)
        resp = await self._aclient().post(
            f"{self._base_url}/add_map", content=data, headers=headers
        )
        resp.raise_for_status()


@cache
def cncstats_client() -> CncstatsClient:
    """Process-wide cncstats client; the httpx connection pool lives as long."""
    parse_token = os.environ.get(PARSE_BEARER_ENV)
    map_api_key = os.environ.get(MAP_API_KEY_ENV)
    logger.info(
        "Building cncstats client",
        parse_token=bool(parse_token),
        map_api_key=bool(map_api_key),
    )
    return CncstatsClient(parse_token=parse_token, map_api_key=map_api_key)
