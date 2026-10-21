"""
firebase_rest.py
Shared, quota-aware Firebase Realtime Database REST client for every PC script.

WHY
---
The Spark (free) plan caps Realtime Database DOWNLOAD at 10 GB/month and
storage at 1 GB. Download is not only the JSON you GET: Firebase also bills
connection/TLS overhead, and every PUT/PATCH echoes the written data back
unless the request asks for `print=silent`. The old scripts opened a fresh
TLS connection for every call (urllib) and polled every 1-5 s, which adds up
to gigabytes per month. This client fixes that in one place:

  * ONE persistent HTTPS connection (http.client keep-alive) per process.
  * All writes use `?print=silent` -> 204 No Content, nothing echoed back.
  * `get(path, shallow=True)` for cheap key listings.
  * Retries with exponential backoff on 429 / 5xx / dropped connections,
    and NO retry storm on 401/403 (bad secret) - it raises immediately.
  * Counts bytes received and appends a per-day tally to
    data/.firebase_usage.json so you can see what the PC side costs.
  * Credentials come ONLY from the environment / project .env file.

Usage
-----
    from firmware.firebase_rest import get_client
    fb = get_client()
    live = fb.get("live")                       # GET /live.json
    keys = fb.get("sessions", shallow=True)     # {"wash_...": true, ...}
    fb.patch("session_meta/abc", {"archived": True})
"""

from __future__ import annotations

# =============================================================================
# SECTION 1: Imports & configuration
# =============================================================================
import http.client
import json
import os
import ssl
import threading
import time
import urllib.parse
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
USAGE_FILE = BASE_DIR / "data" / ".firebase_usage.json"

RETRY_STATUSES = {429, 500, 502, 503, 504}


def load_env(path: Path = ENV_FILE) -> None:
    """Load KEY=VALUE lines from .env into os.environ (existing vars win)."""
    if not path.is_file():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
    except OSError:
        pass


class FirebaseAuthError(RuntimeError):
    """401/403 from Firebase: wrong/rotated secret or rules. Retrying will not help."""


# =============================================================================
# SECTION 2: Client
# =============================================================================
class FirebaseClient:
    """Thread-safe (one lock) keep-alive REST client for one RTDB instance."""

    def __init__(self, host: Optional[str] = None, auth: Optional[str] = None,
                 timeout: float = 10.0, max_retries: int = 4) -> None:
        load_env()
        host = (host or os.environ.get("FIREBASE_HOST") or "").rstrip("/")
        auth = auth or os.environ.get("FIREBASE_AUTH") or os.environ.get("FIREBASE_SECRET")
        if not host:
            raise RuntimeError("FIREBASE_HOST is not set (put it in the project .env)")
        if not auth:
            raise RuntimeError("FIREBASE_AUTH is not set (put it in the project .env) - "
                               "there is deliberately no built-in fallback secret")
        parsed = urllib.parse.urlparse(host)
        self.netloc = parsed.netloc
        self.auth = auth
        self.timeout = timeout
        self.max_retries = max_retries
        self._conn: Optional[http.client.HTTPSConnection] = None
        self._lock = threading.Lock()
        self._ctx = ssl.create_default_context()
        self.bytes_in = 0          # body bytes received this process (headers excluded)
        self.requests = 0

    # ---------------------------------------------------------------- internals
    def _connection(self) -> http.client.HTTPSConnection:
        if self._conn is None:
            self._conn = http.client.HTTPSConnection(self.netloc, timeout=self.timeout, context=self._ctx)
        return self._conn

    def _drop(self) -> None:
        try:
            if self._conn is not None:
                self._conn.close()
        finally:
            self._conn = None

    def _url(self, path: str, params: Dict[str, str]) -> str:
        q = {"auth": self.auth, **params}
        p = "/" + path.strip("/") + ".json"
        return p + "?" + urllib.parse.urlencode(q)

    def _request(self, method: str, path: str, body: Any = None,
                 params: Optional[Dict[str, str]] = None) -> Any:
        params = dict(params or {})
        if method in ("PUT", "PATCH", "POST", "DELETE"):
            params.setdefault("print", "silent")        # no echo of written data
        payload = None if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
        headers = {"Content-Type": "application/json", "Connection": "keep-alive",
                   "User-Agent": "PdM-FirebaseClient/2.0", "Accept-Encoding": "identity"}
        delay = 1.0
        with self._lock:
            for attempt in range(self.max_retries + 1):
                try:
                    conn = self._connection()
                    conn.request(method, self._url(path, params), body=payload, headers=headers)
                    resp = conn.getresponse()
                    data = resp.read()                    # must drain to reuse the socket
                    self.bytes_in += len(data)
                    self.requests += 1
                    if resp.status in (401, 403):
                        raise FirebaseAuthError(f"{method} /{path}: HTTP {resp.status} {data[:200]!r}")
                    if resp.status in RETRY_STATUSES:
                        raise ConnectionError(f"HTTP {resp.status}")
                    if resp.status >= 400:
                        raise RuntimeError(f"{method} /{path}: HTTP {resp.status} {data[:200]!r}")
                    if resp.getheader("Connection", "").lower() == "close":
                        self._drop()
                    if not data:
                        return None
                    return json.loads(data.decode("utf-8"))
                except FirebaseAuthError:
                    raise
                except (ConnectionError, http.client.HTTPException, OSError, ssl.SSLError) as e:
                    self._drop()
                    if attempt >= self.max_retries:
                        raise ConnectionError(f"{method} /{path} failed after {attempt + 1} tries: {e}") from e
                    time.sleep(delay)
                    delay = min(delay * 2, 30.0)
        return None

    # ------------------------------------------------------------------ public
    def get(self, path: str, shallow: bool = False, **params: str) -> Any:
        """GET a node. shallow=True returns only child keys (values -> true)."""
        if shallow:
            params["shallow"] = "true"
        return self._request("GET", path, params=params)

    def put(self, path: str, value: Any) -> None:
        self._request("PUT", path, body=value)

    def patch(self, path: str, value: Dict[str, Any]) -> None:
        self._request("PATCH", path, body=value)

    def delete(self, path: str) -> None:
        self._request("DELETE", path)

    def record_usage(self) -> None:
        """Add this process's received bytes to today's tally in data/.firebase_usage.json."""
        if self.bytes_in == 0 and self.requests == 0:
            return
        try:
            USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
            usage = json.loads(USAGE_FILE.read_text(encoding="utf-8")) if USAGE_FILE.is_file() else {}
            day = date.today().isoformat()
            d = usage.setdefault(day, {"body_bytes_in": 0, "requests": 0})
            d["body_bytes_in"] += self.bytes_in
            d["requests"] += self.requests
            usage["_note"] = ("Body bytes only. Firebase also bills headers + TLS overhead; "
                              "check the console Usage tab for the authoritative number.")
            USAGE_FILE.write_text(json.dumps(usage, indent=2), encoding="utf-8")
            self.bytes_in = 0
            self.requests = 0
        except (OSError, ValueError):
            pass


# =============================================================================
# SECTION 3: Process-wide singleton
# =============================================================================
_client: Optional[FirebaseClient] = None


def get_client() -> FirebaseClient:
    """Return the shared client (created on first use)."""
    global _client
    if _client is None:
        _client = FirebaseClient()
    return _client
