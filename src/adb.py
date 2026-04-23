"""Thin wrapper around uiautomator2 with the UI helpers we need.

uiautomator2 (u2) talks to a small agent installed on the device; it gives us:
- d.click(x, y), d.send_keys, d.screenshot, d.dump_hierarchy
- d(text=..., resourceId=..., className=...) locator objects
"""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path
from typing import Any

import uiautomator2 as u2

log = logging.getLogger(__name__)


class AdbHelper:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 21503,
        adb_path: str = "adb",
        wait_timeout: int = 30,
        action_delay: float = 0.8,
    ):
        self.serial = f"{host}:{port}"
        self.adb_path = adb_path
        self.wait_timeout = wait_timeout
        self.action_delay = action_delay
        self.d: u2.Device | None = None

    # ---------- lifecycle ----------
    def connect(self) -> None:
        self._adb(["connect", self.serial])
        log.info("Connecting uiautomator2 to %s ...", self.serial)
        self.d = u2.connect(self.serial)
        info = self.d.info
        log.info(
            "Connected. device=%s sdk=%s display=%sx%s",
            info.get("productName"),
            info.get("sdkInt"),
            info.get("displayWidth"),
            info.get("displayHeight"),
        )

    def _adb(self, args: list[str]) -> str:
        cmd = [self.adb_path, *args]
        log.debug("$ %s", " ".join(cmd))
        out = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if out.returncode != 0:
            log.warning("adb %s -> rc=%s stderr=%s", args, out.returncode, out.stderr.strip())
        return out.stdout

    @property
    def dev(self) -> u2.Device:
        if self.d is None:
            raise RuntimeError("AdbHelper not connected; call connect() first.")
        return self.d

    # ---------- app ----------
    def start_app(self, package: str, activity: str = "") -> None:
        if activity:
            self.dev.app_start(package, activity=activity, stop=True)
        else:
            self.dev.app_start(package, stop=True)
        log.info("Started app: %s", package)

    def stop_app(self, package: str) -> None:
        try:
            self.dev.app_stop(package)
        except Exception as e:  # noqa: BLE001
            log.warning("stop_app failed: %s", e)

    def clear_app(self, package: str) -> None:
        self._adb(["-s", self.serial, "shell", "pm", "clear", package])

    # ---------- interactions ----------
    def tap(self, x: int, y: int) -> None:
        self.dev.click(x, y)
        time.sleep(self.action_delay)

    def type_text(self, text: str, clear_first: bool = True) -> None:
        if clear_first:
            try:
                self.dev.clear_text()
            except Exception:  # noqa: BLE001
                pass
        self.dev.send_keys(text)
        time.sleep(self.action_delay)

    def press_back(self) -> None:
        self.dev.press("back")
        time.sleep(self.action_delay)

    def press_enter(self) -> None:
        self.dev.press("enter")
        time.sleep(self.action_delay)

    # ---------- locators ----------
    def find(self, **kwargs: Any) -> u2.UiObject:
        return self.dev(**kwargs)

    def wait_for(self, timeout: int | None = None, **kwargs: Any) -> u2.UiObject:
        """Wait until selector exists, else raise."""
        t = timeout if timeout is not None else self.wait_timeout
        obj = self.dev(**kwargs)
        if not obj.wait(timeout=t):
            raise TimeoutError(f"Element not found in {t}s: {kwargs}")
        return obj

    def click_when_ready(self, timeout: int | None = None, **kwargs: Any) -> None:
        obj = self.wait_for(timeout=timeout, **kwargs)
        obj.click()
        time.sleep(self.action_delay)

    def exists(self, **kwargs: Any) -> bool:
        return self.dev(**kwargs).exists

    def click_any(self, locators: list[dict[str, Any]], timeout: int | None = None) -> bool:
        """Try each locator; click first that appears within timeout. Returns True on success."""
        t = timeout if timeout is not None else self.wait_timeout
        deadline = time.time() + t
        while time.time() < deadline:
            for loc in locators:
                obj = self.dev(**loc)
                if obj.exists:
                    obj.click()
                    time.sleep(self.action_delay)
                    return True
            time.sleep(0.5)
        return False

    # ---------- debug ----------
    def screenshot(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self.dev.screenshot(str(p))
        log.debug("Screenshot saved: %s", p)

    def dump_hierarchy(self, path: str | Path) -> str:
        xml = self.dev.dump_hierarchy()
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(xml, encoding="utf-8")
        return xml
