"""Generate data/input_template.xlsx with the required columns + 1 sample row."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.excel_io import ALL_COLUMNS


def main() -> None:
    rows = [
        {
            "first_name": "Ahmad",
            "last_name": "Fadilah",
            "passport_no": "X1234567",
            "visa_no": "12345678",
            "date_of_birth": "1995-03-21",
            "phone_indo": "081234567890",
            "password": "",
            "email": "",
            "email_password": "",
            "status": "PENDING",
            "error": "",
            "account_created_at": "",
        }
    ]
    df = pd.DataFrame(rows, columns=ALL_COLUMNS)
    out = Path("data/input_template.xlsx")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(out, index=False)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
