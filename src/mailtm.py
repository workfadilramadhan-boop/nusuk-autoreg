"""Minimal mail.tm client: create inbox, poll for OTP."""

from __future__ import annotations

import logging
import re
import secrets
import string
import time
from dataclasses import dataclass
from typing import Any

import requests

log = logging.getLogger(__name__)


class MailtmError(RuntimeError):
    pass


@dataclass
class Mailbox:
    address: str
    password: str
    account_id: str
    token: str


class MailtmClient:
    def __init__(self, base_url: str = "https://api.mail.tm", timeout: int = 20):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    # ---------------- public API ----------------
    def create_mailbox(self, local_part: str | None = None) -> Mailbox:
        domain = self._pick_domain()
        local = local_part or self._rand(12)
        address = f"{local}@{domain}"
        password = self._rand(16)
        self._create_account(address, password)
        token, account_id = self._login(address, password)
        log.info("mail.tm inbox ready: %s", address)
        return Mailbox(address=address, password=password, account_id=account_id, token=token)

    def wait_for_otp(
        self,
        box: Mailbox,
        regex: str = r"\b(\d{4,8})\b",
        timeout_sec: int = 120,
        poll_interval_sec: int = 3,
        subject_contains: str | None = None,
    ) -> str:
        """Block until an OTP-like code arrives, return the code string."""
        pattern = re.compile(regex)
        deadline = time.time() + timeout_sec
        seen_ids: set[str] = set()
        while time.time() < deadline:
            for msg in self._list_messages(box):
                mid = msg.get("id")
                if not mid or mid in seen_ids:
                    continue
                seen_ids.add(mid)
                subj = (msg.get("subject") or "")
                if subject_contains and subject_contains.lower() not in subj.lower():
                    continue
                full = self._get_message(box, mid)
                body = self._extract_body(full)
                m = pattern.search(body) or pattern.search(subj)
                if m:
                    code = m.group(1)
                    log.info("OTP received: %s (subject=%r)", code, subj)
                    return code
            time.sleep(poll_interval_sec)
        raise MailtmError(f"OTP tidak masuk dalam {timeout_sec}s untuk {box.address}")

    # ---------------- internals ----------------
    def _pick_domain(self) -> str:
        r = self.session.get(f"{self.base}/domains", timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        # API bisa return paginated {"hydra:member": [...]} atau list biasa.
        items = data.get("hydra:member", data) if isinstance(data, dict) else data
        active = [d for d in items if d.get("isActive", True)]
        if not active:
            raise MailtmError("Tidak ada domain mail.tm aktif")
        return active[0]["domain"]

    def _create_account(self, address: str, password: str) -> None:
        r = self.session.post(
            f"{self.base}/accounts",
            json={"address": address, "password": password},
            timeout=self.timeout,
        )
        if r.status_code not in (200, 201):
            raise MailtmError(f"Gagal create mailbox: {r.status_code} {r.text[:200]}")

    def _login(self, address: str, password: str) -> tuple[str, str]:
        r = self.session.post(
            f"{self.base}/token",
            json={"address": address, "password": password},
            timeout=self.timeout,
        )
        r.raise_for_status()
        data = r.json()
        return data["token"], data.get("id", "")

    def _auth_headers(self, box: Mailbox) -> dict[str, str]:
        return {"Authorization": f"Bearer {box.token}"}

    def _list_messages(self, box: Mailbox) -> list[dict[str, Any]]:
        r = self.session.get(
            f"{self.base}/messages",
            headers=self._auth_headers(box),
            timeout=self.timeout,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("hydra:member", data) if isinstance(data, dict) else data

    def _get_message(self, box: Mailbox, message_id: str) -> dict[str, Any]:
        r = self.session.get(
            f"{self.base}/messages/{message_id}",
            headers=self._auth_headers(box),
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()

    @staticmethod
    def _extract_body(msg: dict[str, Any]) -> str:
        parts: list[str] = []
        if msg.get("text"):
            parts.append(str(msg["text"]))
        html = msg.get("html")
        if isinstance(html, list):
            parts.extend(str(x) for x in html)
        elif isinstance(html, str):
            parts.append(html)
        if msg.get("intro"):
            parts.append(str(msg["intro"]))
        return "\n".join(parts)

    @staticmethod
    def _rand(n: int) -> str:
        alpha = string.ascii_lowercase + string.digits
        return "".join(secrets.choice(alpha) for _ in range(n))
