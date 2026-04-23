"""Small utilities: logging setup, password gen, phone normalize, delays."""

from __future__ import annotations

import logging
import random
import re
import secrets
import string
import time
from pathlib import Path


def setup_logging(logs_dir: str | Path, verbose: bool = False) -> None:
    p = Path(logs_dir)
    p.mkdir(parents=True, exist_ok=True)
    logfile = p / f"run-{time.strftime('%Y%m%d-%H%M%S')}.log"
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handlers: list[logging.Handler] = [
        logging.FileHandler(logfile, encoding="utf-8"),
        logging.StreamHandler(),
    ]
    logging.basicConfig(level=level, format=fmt, handlers=handlers, force=True)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)


def generate_password(length: int = 12) -> str:
    """Password Nusuk butuh: >= 8 char, upper, lower, digit, special."""
    if length < 8:
        length = 8
    specials = "!@#$%^&*"
    pools = [
        string.ascii_uppercase,
        string.ascii_lowercase,
        string.digits,
        specials,
    ]
    # satu char wajib dari tiap pool
    chars = [secrets.choice(pool) for pool in pools]
    all_chars = "".join(pools)
    chars += [secrets.choice(all_chars) for _ in range(length - len(chars))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def normalize_indo_phone(raw: str) -> str:
    """Return phone as local number without country prefix.
    Nusuk biasanya sudah punya dropdown +62, jadi kita masukkan bagian
    setelah kode negara, diawali 8 (misal 81234567890).
    """
    s = re.sub(r"\D", "", raw or "")
    if s.startswith("62"):
        s = s[2:]
    if s.startswith("0"):
        s = s[1:]
    return s


def normalize_dob(raw: str) -> tuple[str, str, str]:
    """Parse date of birth ke tuple (day, month, year) 2 digit / 4 digit.
    Menerima: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY.
    """
    s = (raw or "").strip()
    for sep in ("-", "/", " "):
        if sep in s:
            parts = [p for p in s.split(sep) if p]
            break
    else:
        raise ValueError(f"Format tanggal tidak dikenali: {raw!r}")
    if len(parts) != 3:
        raise ValueError(f"Format tanggal tidak dikenali: {raw!r}")
    # Kalau angka pertama 4 digit -> YYYY-MM-DD
    if len(parts[0]) == 4:
        y, m, d = parts
    else:
        d, m, y = parts
    return d.zfill(2), m.zfill(2), y.zfill(4) if len(y) == 4 else f"20{y.zfill(2)}"


def sleep_jitter(base: float, jitter: float = 0.3) -> None:
    time.sleep(max(0.0, base + random.uniform(-jitter, jitter)))


def sleep_between_accounts(min_s: int, max_s: int) -> None:
    time.sleep(random.uniform(min_s, max_s))
