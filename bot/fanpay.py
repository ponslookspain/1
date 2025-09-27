"""FanPay client abstraction for creating listings via HTTP requests."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Union

import requests


class FanPayError(Exception):
    """Raised when FanPay returns an unexpected response."""


@dataclass
class Listing:
    """Simple data holder for a FanPay listing."""

    name: str
    description: str
    price: float
    quantity: int


class FanPayClient:
    """HTTP client that reuses a cookie jar to authenticate with FanPay.

    The actual FanPay API is not publicly documented. This client focuses on
    the pieces that are known to be required for creating a listing: an
    authenticated session (expressed as a cookie jar) and CSRF token.
    """

    def __init__(
        self,
        base_url: str = "https://funpay.com",
        *,
        cookie_file: Optional[Union[str, Path]] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()
        if cookie_file is not None:
            self._load_cookies(cookie_file)
        self.session.headers.setdefault("User-Agent", "FanPayBot/1.0")
        self.session.headers.setdefault("Accept", "application/json")
        if extra_headers:
            self.session.headers.update(extra_headers)

    # ------------------------------------------------------------------
    # Cookie helpers
    # ------------------------------------------------------------------
    def _load_cookies(self, cookie_file: Union[str, Path]) -> None:
        """Load cookies from a Netscape formatted file."""
        jar = requests.cookies.RequestsCookieJar()
        content = Path(cookie_file).read_text(encoding="utf-8")
        for line in content.splitlines():
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) != 7:
                continue
            domain, flag, path, secure, expiration, name, value = parts
            jar.set(
                name,
                value,
                domain=domain,
                path=path,
                secure=secure.upper() == "TRUE",
            )
        self.session.cookies.update(jar)

    # ------------------------------------------------------------------
    # API operations
    # ------------------------------------------------------------------
    def create_listing(self, listing: Listing, csrf_token: Optional[str] = None) -> dict:
        """Create a FanPay listing.

        Parameters
        ----------
        listing:
            Listing data provided by the user.
        csrf_token:
            Optional CSRF token. When ``None`` the method attempts to reuse
            the value already stored in the session cookies.

        Returns
        -------
        dict
            Parsed JSON response for further processing.
        """

        payload = {
            "title": listing.name,
            "description": listing.description,
            "price": listing.price,
            "quantity": listing.quantity,
        }

        headers = {}
        token = csrf_token or self.session.cookies.get("csrftoken")
        if token:
            headers["X-CSRFToken"] = token

        url = f"{self.base_url}/api/listings"
        response = self.session.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code >= 400:
            raise FanPayError(
                f"FanPay error {response.status_code}: {response.text}".strip()
            )
        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise FanPayError("FanPay returned invalid JSON response") from exc
