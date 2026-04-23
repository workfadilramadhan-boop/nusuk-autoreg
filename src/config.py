"""Load & validate configuration from YAML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AdbConfig:
    host: str = "127.0.0.1"
    port: int = 21503
    adb_path: str = "adb"

    @property
    def serial(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass
class NusukConfig:
    package: str = "sa.gov.mcit.hajj"
    activity: str = ""
    wait_timeout: int = 30
    action_delay: float = 0.8


@dataclass
class IoConfig:
    input_xlsx: str = "data/input.xlsx"
    output_xlsx: str = "output/results.xlsx"
    logs_dir: str = "output/logs"
    screenshots_dir: str = "output/screenshots"


@dataclass
class MailtmConfig:
    base_url: str = "https://api.mail.tm"
    otp_poll_interval_sec: int = 3
    otp_timeout_sec: int = 120
    otp_regex: str = r"\b(\d{4,8})\b"


@dataclass
class RunConfig:
    between_accounts_sec_min: int = 5
    between_accounts_sec_max: int = 15
    max_retries: int = 1
    screenshot_each_step: bool = False


@dataclass
class Config:
    adb: AdbConfig = field(default_factory=AdbConfig)
    nusuk: NusukConfig = field(default_factory=NusukConfig)
    io: IoConfig = field(default_factory=IoConfig)
    mailtm: MailtmConfig = field(default_factory=MailtmConfig)
    run: RunConfig = field(default_factory=RunConfig)


def _merge(section_cls: type, raw: dict[str, Any] | None) -> Any:
    if not raw:
        return section_cls()
    allowed = {f.name for f in section_cls.__dataclass_fields__.values()}
    return section_cls(**{k: v for k, v in raw.items() if k in allowed})


def load_config(path: str | Path) -> Config:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Config tidak ditemukan: {p}. Copy config.example.yaml -> config.yaml dulu."
        )
    with p.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return Config(
        adb=_merge(AdbConfig, raw.get("adb")),
        nusuk=_merge(NusukConfig, raw.get("nusuk")),
        io=_merge(IoConfig, raw.get("io")),
        mailtm=_merge(MailtmConfig, raw.get("mailtm")),
        run=_merge(RunConfig, raw.get("run")),
    )
