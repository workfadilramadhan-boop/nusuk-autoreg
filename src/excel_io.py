"""Read input Excel & write results back."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

# Kolom yang user isi
INPUT_COLUMNS = [
    "first_name",
    "last_name",
    "passport_no",
    "visa_no",
    "date_of_birth",   # format: YYYY-MM-DD, atau apapun yang bisa di-parse pandas
    "phone_indo",      # boleh dengan / tanpa +62, bot normalize
    "password",        # boleh kosong, bot generate kalau kosong
]

# Kolom yang bot isi otomatis
OUTPUT_COLUMNS = [
    "email",
    "email_password",
    "status",          # PENDING | SUCCESS | FAILED
    "error",
    "account_created_at",
]

ALL_COLUMNS = INPUT_COLUMNS + OUTPUT_COLUMNS


@dataclass
class AccountRow:
    index: int
    first_name: str
    last_name: str
    passport_no: str
    visa_no: str
    date_of_birth: str
    phone_indo: str
    password: str = ""
    email: str = ""
    email_password: str = ""
    status: str = "PENDING"
    error: str = ""
    account_created_at: str = ""
    _extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        d = {c: getattr(self, c, "") for c in ALL_COLUMNS}
        d.update(self._extra)
        return d


def _coerce(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    if isinstance(v, pd.Timestamp):
        return v.strftime("%Y-%m-%d")
    return str(v).strip()


def read_accounts(xlsx_path: str | Path) -> list[AccountRow]:
    p = Path(xlsx_path)
    if not p.exists():
        raise FileNotFoundError(f"Input Excel tidak ditemukan: {p}")
    df = pd.read_excel(p, dtype=object)
    for col in INPUT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    rows: list[AccountRow] = []
    for idx, raw in df.iterrows():
        rows.append(
            AccountRow(
                index=int(idx),  # type: ignore[arg-type]
                first_name=_coerce(raw.get("first_name")),
                last_name=_coerce(raw.get("last_name")),
                passport_no=_coerce(raw.get("passport_no")),
                visa_no=_coerce(raw.get("visa_no")),
                date_of_birth=_coerce(raw.get("date_of_birth")),
                phone_indo=_coerce(raw.get("phone_indo")),
                password=_coerce(raw.get("password")),
                email=_coerce(raw.get("email")),
                email_password=_coerce(raw.get("email_password")),
                status=_coerce(raw.get("status")) or "PENDING",
                error=_coerce(raw.get("error")),
                account_created_at=_coerce(raw.get("account_created_at")),
            )
        )
    return rows


def pending_rows(rows: list[AccountRow]) -> Iterator[AccountRow]:
    for r in rows:
        if r.status != "SUCCESS":
            yield r


def write_results(xlsx_path: str | Path, rows: list[AccountRow]) -> None:
    p = Path(xlsx_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([r.as_dict() for r in rows], columns=ALL_COLUMNS)
    df.to_excel(p, index=False)


def mark_success(row: AccountRow) -> None:
    row.status = "SUCCESS"
    row.error = ""
    row.account_created_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def mark_failed(row: AccountRow, err: str) -> None:
    row.status = "FAILED"
    row.error = err[:500]


def validate_row(row: AccountRow) -> list[str]:
    """Return list of missing/invalid fields. Empty list = OK."""
    problems: list[str] = []
    if not row.first_name:
        problems.append("first_name kosong")
    if not row.last_name:
        problems.append("last_name kosong")
    if not row.passport_no:
        problems.append("passport_no kosong")
    if not row.visa_no:
        problems.append("visa_no kosong")
    if not row.date_of_birth:
        problems.append("date_of_birth kosong")
    if not row.phone_indo:
        problems.append("phone_indo kosong")
    return problems
