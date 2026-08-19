"""Enphase Enlighten API client for Battery RBD control.

Key insight: the batterySettings PUT endpoint with rbdControl.enabled
requires a fully authenticated Enlighten session (cookie jar + XSRF token).
A simple JWT alone returns 403. This client replicates the browser session
the Enphase app uses when you toggle 'Restrict battery discharge'.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import aiohttp

from .const import (
    BATTERY_CONFIG_BASE,
    BATTERY_PROFILE_ORIGIN,
    ENLIGHTEN_BASE,
)

_LOGGER = logging.getLogger(__name__)

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0 Safari/537.36"
)


class EnlightenAuthError(Exception):
    """Raised when authentication fails."""


class EnlightenApiError(Exception):
    """Raised when an API call fails."""


def _decode_jwt_exp(token: str) -> int:
    """Return the exp claim from a JWT, or 0 on failure."""
    try:
        payload = token.split(".")[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding
        payload = payload.replace("-", "+").replace("_", "/")
        claims = json.loads(base64.b64decode(payload))
        return int(claims.get("exp", 0))
    except Exception:
        return 0


class EnlightenSession:
    """Manages an authenticated Enlighten cloud session.

    Authentication flow mirrors the Enphase battery-profile-ui web app:
    1. GET /login  →  extract CSRF authenticity_token
    2. POST /login/login  →  establish session cookies
    3. GET /app-api/jwt_token.json  →  retrieve JWT
    4. GET /  →  follow redirect to discover site_id (= battery_id)
    5. GET /app-api/{site_id}/data.json  →  extract user_id
    6. POST /schedules/isValid  →  receive BP-XSRF-Token cookie

    After setup, set_rbd_enabled() calls:
      PUT /batterySettings/{battery_id}?userId={user_id}&source=enho
      { "rbdControl": { "enabled": true|false } }
    """

    def __init__(
        self,
        email: str,
        password: str,
        battery_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        self._email = email
        self._password = password
        self._battery_id = battery_id
        self._user_id = user_id
        self._jwt: str | None = None
        self._jwt_exp: int = 0
        self._xsrf: str | None = None
        self._session: aiohttp.ClientSession | None = None

    # ── Session lifecycle ─────────────────────────────────────────────────────

    def _make_session(self) -> aiohttp.ClientSession:
        return aiohttp.ClientSession(
            cookie_jar=aiohttp.CookieJar(unsafe=True),
            headers={"User-Agent": _BROWSER_UA},
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = self._make_session()
        return self._session

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    # ── Authentication ────────────────────────────────────────────────────────

    def _jwt_valid(self) -> bool:
        """Return True if the JWT is present and won't expire within 1 hour."""
        if not self._jwt:
            return False
        now = int(datetime.now(timezone.utc).timestamp())
        return self._jwt_exp > now + 3600

    async def login(self) -> None:
        """Perform a full Enlighten login, including ID discovery."""
        _LOGGER.debug("Performing full Enlighten login for %s", self._email)
        session = await self._get_session()

        # Step 1: Get Rails CSRF token
        async with session.get(f"{ENLIGHTEN_BASE}/login") as resp:
            if resp.status != 200:
                raise EnlightenAuthError(
                    f"Could not reach Enlighten login page: HTTP {resp.status}"
                )
            text = await resp.text()

        match = re.search(r'name="authenticity_token" value="([^"]+)"', text)
        if not match:
            raise EnlightenAuthError("Could not find authenticity_token on login page")
        auth_token = match.group(1)

        # Step 2: Submit credentials
        async with session.post(
            f"{ENLIGHTEN_BASE}/login/login",
            data={
                "utf8": "\u2713",
                "authenticity_token": auth_token,
                "user[email]": self._email,
                "user[password]": self._password,
            },
            allow_redirects=True,
        ) as resp:
            if resp.status not in (200, 302):
                raise EnlightenAuthError(
                    f"Login POST failed: HTTP {resp.status}"
                )

        # Step 3: Get JWT
        async with session.get(
            f"{ENLIGHTEN_BASE}/app-api/jwt_token.json"
        ) as resp:
            if resp.status != 200:
                raise EnlightenAuthError(
                    f"JWT endpoint returned HTTP {resp.status} — check credentials"
                )
            data = await resp.json()

        self._jwt = data.get("token")
        if not self._jwt:
            raise EnlightenAuthError(
                "JWT not returned — email or password may be incorrect"
            )
        self._jwt_exp = _decode_jwt_exp(self._jwt)
        _LOGGER.debug("JWT obtained, expires at %s", self._jwt_exp)

        # Step 4 & 5: Discover battery_id and user_id if not stored
        if not self._battery_id or not self._user_id:
            await self._discover_ids(session)

    async def _discover_ids(self, session: aiohttp.ClientSession) -> None:
        """Auto-discover battery_id (site ID) and user_id from the Enlighten session."""
        async with session.get(
            f"{ENLIGHTEN_BASE}/", allow_redirects=True
        ) as resp:
            final_url = str(resp.url)

        match = re.search(
            r"/(web|pv/systems|systems)/(\d+)", final_url
        )
        if not match:
            raise EnlightenAuthError(
                f"Could not extract site ID from URL: {final_url}"
            )
        site_id = match.group(2)

        async with session.get(
            f"{ENLIGHTEN_BASE}/app-api/{site_id}/data.json"
            "?app=1&device_status=non_retired&is_mobile=0"
        ) as resp:
            if resp.status != 200:
                raise EnlightenAuthError(
                    f"Could not fetch site data: HTTP {resp.status}"
                )
            data = await resp.json()

        app = data.get("app", {})
        user_id = (
            app.get("userId")
            or app.get("user_id")
            or (app.get("user") or {}).get("id")
        )
        if not user_id:
            raise EnlightenAuthError("Could not extract user ID from site data")

        self._battery_id = site_id
        self._user_id = str(user_id)
        _LOGGER.debug(
            "Discovered battery_id=%s user_id=%s", self._battery_id, self._user_id
        )

    async def _refresh_xsrf(self) -> None:
        """Obtain a fresh BP-XSRF-Token by calling the schedule isValid endpoint."""
        session = await self._get_session()
        url = (
            f"{BATTERY_CONFIG_BASE}/battery/sites"
            f"/{self._battery_id}/schedules/isValid"
        )
        headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "e-auth-token": self._jwt,
            "username": self._user_id,
            "origin": BATTERY_PROFILE_ORIGIN,
            "referer": f"{BATTERY_PROFILE_ORIGIN}/",
        }
        async with session.post(
            url, json={"scheduleType": "rbd"}, headers=headers
        ) as resp:
            _ = await resp.read()  # consume body

        # Extract from cookie jar
        self._xsrf = None
        for cookie in session.cookie_jar:
            if cookie.key == "BP-XSRF-Token":
                self._xsrf = cookie.value
                break

        if not self._xsrf:
            _LOGGER.warning("BP-XSRF-Token not returned by isValid endpoint")

    async def ensure_authenticated(self) -> None:
        """Ensure a valid JWT and fresh XSRF token are available."""
        if not self._jwt_valid():
            await self.login()
        await self._refresh_xsrf()

    # ── Battery RBD control ───────────────────────────────────────────────────

    def _rbd_headers(self) -> dict[str, str]:
        """Return headers required for the batterySettings PUT."""
        return {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "e-auth-token": self._jwt or "",
            "x-xsrf-token": self._xsrf or "",
            "username": self._user_id or "",
            "origin": BATTERY_PROFILE_ORIGIN,
            "referer": f"{BATTERY_PROFILE_ORIGIN}/",
            "user-agent": _BROWSER_UA,
        }

    async def set_rbd_enabled(self, enabled: bool) -> None:
        """Enable or disable Restrict Battery Discharge.

        PUT /batterySettings/{battery_id}?userId={user_id}&source=enho
        { "rbdControl": { "enabled": true|false } }

        Requires a fully authenticated session with XSRF token.
        Returns without error on HTTP 200; raises EnlightenApiError otherwise.
        """
        await self.ensure_authenticated()
        session = await self._get_session()

        url = (
            f"{BATTERY_CONFIG_BASE}/batterySettings/{self._battery_id}"
            f"?userId={self._user_id}&source=enho"
        )
        payload = {"rbdControl": {"enabled": enabled}}

        _LOGGER.debug(
            "PUT batterySettings rbdControl.enabled=%s for battery %s",
            enabled,
            self._battery_id,
        )

        async with session.put(
            url, json=payload, headers=self._rbd_headers()
        ) as resp:
            if resp.status == 200:
                _LOGGER.debug("RBD %s successful", "enabled" if enabled else "disabled")
                return
            text = await resp.text()
            raise EnlightenApiError(
                f"batterySettings PUT returned HTTP {resp.status}: {text}"
            )

    def _schedule_headers(self) -> dict[str, str]:
        """Return headers required for the schedule API calls."""
        return {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "e-auth-token": self._jwt or "",
            "x-xsrf-token": self._xsrf or "",
            "username": self._user_id or "",
            "origin": BATTERY_PROFILE_ORIGIN,
            "referer": f"{BATTERY_PROFILE_ORIGIN}/",
            "user-agent": _BROWSER_UA,
        }

    async def _delete_all_rbd_schedules(self, session: aiohttp.ClientSession) -> None:
        """Delete all existing RBD schedules to avoid 409 conflicts."""
        url = f"{BATTERY_CONFIG_BASE}/battery/sites/{self._battery_id}/schedules"
        async with session.get(url, headers=self._schedule_headers()) as resp:
            if resp.status != 200:
                return
            data = await resp.json()

        rbd_details = (data.get("rbd") or {}).get("details") or []
        for sched in rbd_details:
            schedule_id = sched.get("scheduleId")
            if not schedule_id:
                continue
            delete_url = f"{url}/{schedule_id}/delete"
            try:
                async with session.post(
                    delete_url,
                    json={},
                    headers=self._schedule_headers(),
                ) as resp:
                    _LOGGER.debug(
                        "Deleted RBD schedule %s: HTTP %s", schedule_id, resp.status
                    )
            except Exception as exc:
                _LOGGER.warning("Could not delete schedule %s: %s", schedule_id, exc)

    async def create_default_schedule(self, timezone: str = "UTC") -> None:
        """Create a default 00:00–23:59 all-days RBD schedule.

        Deletes any existing RBD schedules first to avoid 409 conflicts.
        This is the schedule the RBD master switch acts upon — without at
        least one schedule the switch has no effect at the hardware level.
        """
        await self.ensure_authenticated()
        session = await self._get_session()

        _LOGGER.debug("Creating default RBD schedule (00:00–23:59, all days)")

        # Clean up existing schedules first
        await self._delete_all_rbd_schedules(session)

        import asyncio
        await asyncio.sleep(2)

        url = f"{BATTERY_CONFIG_BASE}/battery/sites/{self._battery_id}/schedules"
        payload = {
            "timezone": timezone,
            "startTime": "00:00",
            "endTime": "23:59",
            "limit": 100,
            "scheduleType": "RBD",
            "days": [1, 2, 3, 4, 5, 6, 7],
        }

        async with session.post(
            url, json=payload, headers=self._schedule_headers()
        ) as resp:
            if resp.status in (200, 201):
                data = await resp.json()
                _LOGGER.debug(
                    "Default RBD schedule created: %s", data.get("scheduleId")
                )
            else:
                text = await resp.text()
                raise EnlightenApiError(
                    f"Failed to create default schedule: HTTP {resp.status} — {text}"
                )

    async def get_rbd_status(self) -> bool | None:
        """Return current RBD enabled state, or None if unknown.

        Reads from the battery schedule list. Returns True if the
        Enlighten UI shows RBD as enabled (active schedule present),
        False if disabled, or None if the status cannot be determined.
        """
        await self.ensure_authenticated()
        session = await self._get_session()

        url = f"{BATTERY_CONFIG_BASE}/battery/sites/{self._battery_id}/schedules"
        headers = {
            "accept": "application/json, text/plain, */*",
            "e-auth-token": self._jwt or "",
            "x-xsrf-token": self._xsrf or "",
            "username": self._user_id or "",
            "origin": BATTERY_PROFILE_ORIGIN,
            "referer": f"{BATTERY_PROFILE_ORIGIN}/",
        }

        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    _LOGGER.debug("Schedule list returned HTTP %s", resp.status)
                    return None
                data = await resp.json()
        except Exception as exc:
            _LOGGER.debug("Could not fetch schedule list: %s", exc)
            return None

        # An active, enabled RBD schedule means restriction is on
        rbd_details = (data.get("rbd") or {}).get("details") or []
        for sched in rbd_details:
            if sched.get("isEnabled") and sched.get("scheduleStatus") == "active":
                return True

        # No active RBD schedule found — restriction is off
        # (could also mean the rbdControl master switch is off)
        return False

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def battery_id(self) -> str | None:
        return self._battery_id

    @property
    def user_id(self) -> str | None:
        return self._user_id

    @property
    def is_authenticated(self) -> bool:
        return self._jwt_valid() and bool(self._xsrf)
