"""
Licensing and trial management for Automation Orchestrator.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

LICENSE_SECRET = os.getenv("LICENSE_SECRET", "change-me-in-production-use-strong-secret")
DEFAULT_LICENSE_SECRET = "change-me-in-production-use-strong-secret"


@dataclass
class LicenseStatus:
    status: str
    trial_days_remaining: int
    trial_expires_at: Optional[str]
    license_expires_at: Optional[str]
    purchase_url: str
    demo_mode: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "trial_days_remaining": self.trial_days_remaining,
            "trial_expires_at": self.trial_expires_at,
            "license_expires_at": self.license_expires_at,
            "purchase_url": self.purchase_url,
            "demo_mode": self.demo_mode
        }


class LicenseManager:
    """Handles trial and license enforcement."""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.enabled = config.get("enabled", True)
        self.trial_days = int(config.get("trial_days", 7))
        self.state_path = Path(config.get("state_path", "config/license_state.json"))
        self.purchase_url = config.get("purchase_url", "https://example.com/buy")
        self.demo_allowlist = config.get("demo_allowlist", self._default_demo_allowlist())
        self.demo_write_allowlist = config.get("demo_write_allowlist", ["/api/license/activate"])
        self._state: Dict[str, Any] = {}
        self._load_state()

    def is_default_secret(self) -> bool:
        return LICENSE_SECRET == DEFAULT_LICENSE_SECRET

    def ensure_trial_started(self) -> None:
        if not self.enabled:
            return
        if not self._state.get("trial_start_at"):
            now = self._utcnow().isoformat()
            self._state["trial_start_at"] = now
            self._save_state()

    def get_status(self) -> LicenseStatus:
        if not self.enabled:
            return LicenseStatus(
                status="disabled",
                trial_days_remaining=0,
                trial_expires_at=None,
                license_expires_at=None,
                purchase_url=self.purchase_url,
                demo_mode=False
            )

        now = self._utcnow()
        license_payload = self._get_license_payload()
        if license_payload:
            expires_at = license_payload.get("expires_at")
            if not expires_at or now <= self._parse_dt(expires_at):
                return LicenseStatus(
                    status="active",
                    trial_days_remaining=0,
                    trial_expires_at=None,
                    license_expires_at=expires_at,
                    purchase_url=self.purchase_url,
                    demo_mode=False
                )

        trial_start = self._state.get("trial_start_at")
        if trial_start:
            start_dt = self._parse_dt(trial_start)
            trial_end = start_dt + timedelta(days=self.trial_days)
            if now <= trial_end:
                remaining = max(0, (trial_end - now).days)
                return LicenseStatus(
                    status="trial",
                    trial_days_remaining=remaining,
                    trial_expires_at=trial_end.isoformat(),
                    license_expires_at=None,
                    purchase_url=self.purchase_url,
                    demo_mode=False
                )

        return LicenseStatus(
            status="demo",
            trial_days_remaining=0,
            trial_expires_at=None,
            license_expires_at=None,
            purchase_url=self.purchase_url,
            demo_mode=True
        )

    def is_request_allowed(self, path: str, method: str, status: LicenseStatus) -> bool:
        if not self.enabled:
            return True
        if status.status in {"active", "trial"}:
            return True
        if status.status != "demo":
            return False

        if method in {"GET", "HEAD", "OPTIONS"}:
            return self._path_allowed(path, self.demo_allowlist)

        return self._path_allowed(path, self.demo_write_allowlist)

    def activate_license(self, license_key: str) -> Dict[str, Any]:
        payload = self._validate_license_key(license_key)
        self._state["license_key"] = license_key
        self._state["license_payload"] = payload
        self._state["license_activated_at"] = self._utcnow().isoformat()
        self._save_state()
        return payload

    def _get_license_payload(self) -> Optional[Dict[str, Any]]:
        payload = self._state.get("license_payload")
        if payload and isinstance(payload, dict):
            return payload
        key = self._state.get("license_key")
        if not key:
            return None
        try:
            payload = self._validate_license_key(key)
            self._state["license_payload"] = payload
            self._save_state()
            return payload
        except ValueError:
            return None

    def _load_state(self) -> None:
        if not self.state_path.exists():
            return
        try:
            self._state = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            self._state = {}

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self._state, indent=2), encoding="utf-8")

    def _validate_license_key(self, license_key: str) -> Dict[str, Any]:
        if not license_key:
            raise ValueError("License key is required")

        key = license_key.strip()
        if key.startswith("LIC-"):
            key = key[4:]

        parts = key.split(".")
        if len(parts) != 2:
            raise ValueError("Invalid license key format")

        payload_b64, sig = parts
        expected_sig = self._sign(payload_b64)
        if not hmac.compare_digest(sig, expected_sig):
            raise ValueError("Invalid license signature")

        payload_json = self._b64url_decode(payload_b64).decode("utf-8")
        payload = json.loads(payload_json)

        expires_at = payload.get("expires_at")
        if expires_at and self._utcnow() > self._parse_dt(expires_at):
            raise ValueError("License has expired")

        return payload

    def _sign(self, payload_b64: str) -> str:
        digest = hmac.new(
            LICENSE_SECRET.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256
        ).digest()
        return self._b64url_encode(digest)

    @staticmethod
    def _b64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    @staticmethod
    def _b64url_decode(data: str) -> bytes:
        padding = "=" * (-len(data) % 4)
        return base64.urlsafe_b64decode(data + padding)

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _parse_dt(value: str) -> datetime:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S%z")

    @staticmethod
    def _default_demo_allowlist() -> List[str]:
        return [
            "/",
            "/health",
            "/health/detailed",
            "/metrics",
            "/api/docs",
            "/api/openapi.json",
            "/openapi.json",
            "/redoc",
            "/api/analytics/",
            "/api/workflows/",
            "/api/leads",
            "/api/leads/",
            "/api/campaigns",
            "/api/campaigns/",
            "/api/crm/status",
            "/api/auth/me",
            "/api/license/status",
            "/api/license/purchase"
        ]

    @staticmethod
    def _path_allowed(path: str, patterns: List[str]) -> bool:
        for pattern in patterns:
            if pattern.endswith("/"):
                if path.startswith(pattern):
                    return True
            if pattern.endswith("*"):
                if path.startswith(pattern[:-1]):
                    return True
            if path == pattern:
                return True
        return False
