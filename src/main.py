"""CLI entry point: jalankan bot registrasi Nusuk dari Excel."""

from __future__ import annotations

import argparse
import logging
import sys
import traceback
from pathlib import Path

from .adb import AdbHelper
from .config import Config, load_config
from .excel_io import (
    AccountRow,
    mark_failed,
    mark_success,
    pending_rows,
    read_accounts,
    validate_row,
    write_results,
)
from .mailtm import MailtmClient
from .nusuk_flow import register
from .utils import setup_logging, sleep_between_accounts

log = logging.getLogger("nusuk")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="nusuk-autoreg",
        description="Bot auto-registrasi Nusuk dari Excel ke emulator MEmu.",
    )
    p.add_argument(
        "--config",
        default="config.yaml",
        help="Path ke config YAML (default: ./config.yaml).",
    )
    p.add_argument(
        "--input",
        default=None,
        help="Override path input Excel dari config.",
    )
    p.add_argument(
        "--output",
        default=None,
        help="Override path output Excel dari config.",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Batasi jumlah akun yang diproses (0 = semua).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Hanya validasi input Excel, tidak connect ADB / mail.tm.",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Logging level DEBUG.",
    )
    return p


def process_one(
    cfg: Config,
    adb: AdbHelper,
    mailtm: MailtmClient,
    row: AccountRow,
) -> None:
    last_err: Exception | None = None
    attempts = cfg.run.max_retries + 1
    for attempt in range(1, attempts + 1):
        try:
            log.info(
                "Row %s: registering %s %s (attempt %s/%s)",
                row.index, row.first_name, row.last_name, attempt, attempts,
            )
            register(
                adb=adb,
                mailtm=mailtm,
                row=row,
                package=cfg.nusuk.package,
                activity=cfg.nusuk.activity,
                otp_regex=cfg.mailtm.otp_regex,
                otp_timeout_sec=cfg.mailtm.otp_timeout_sec,
                otp_poll_interval_sec=cfg.mailtm.otp_poll_interval_sec,
            )
            mark_success(row)
            log.info("Row %s: SUCCESS (%s)", row.index, row.email)
            return
        except Exception as e:  # noqa: BLE001
            last_err = e
            err = f"{type(e).__name__}: {e}"
            log.error("Row %s attempt %s failed: %s", row.index, attempt, err)
            log.debug(traceback.format_exc())
            # Screenshot error state
            try:
                shot = Path(cfg.io.screenshots_dir) / f"row{row.index:04d}-attempt{attempt}.png"
                adb.screenshot(shot)
            except Exception:  # noqa: BLE001
                pass
    mark_failed(row, f"{type(last_err).__name__}: {last_err}")


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    if args.input:
        cfg.io.input_xlsx = args.input
    if args.output:
        cfg.io.output_xlsx = args.output

    setup_logging(cfg.io.logs_dir, verbose=args.verbose)
    log.info("Nusuk auto-registration starting")
    log.info("Input : %s", cfg.io.input_xlsx)
    log.info("Output: %s", cfg.io.output_xlsx)

    rows = read_accounts(cfg.io.input_xlsx)
    log.info("Loaded %s rows", len(rows))
    todo = list(pending_rows(rows))
    if args.limit > 0:
        todo = todo[: args.limit]
    log.info("%s rows to process", len(todo))

    # Validate all first
    bad = []
    for r in todo:
        problems = validate_row(r)
        if problems:
            bad.append((r.index, problems))
    if bad:
        for idx, probs in bad:
            log.error("Row %s: %s", idx, "; ".join(probs))
        log.error("Ada %s row invalid. Perbaiki Excel lalu ulangi.", len(bad))
        if not args.dry_run:
            return 2

    if args.dry_run:
        log.info("Dry run selesai. Data valid.")
        return 0

    adb = AdbHelper(
        host=cfg.adb.host,
        port=cfg.adb.port,
        adb_path=cfg.adb.adb_path,
        wait_timeout=cfg.nusuk.wait_timeout,
        action_delay=cfg.nusuk.action_delay,
    )
    adb.connect()
    mailtm = MailtmClient(base_url=cfg.mailtm.base_url)

    try:
        for i, row in enumerate(todo, start=1):
            process_one(cfg, adb, mailtm, row)
            write_results(cfg.io.output_xlsx, rows)  # persist after every row
            if i < len(todo):
                sleep_between_accounts(
                    cfg.run.between_accounts_sec_min,
                    cfg.run.between_accounts_sec_max,
                )
    finally:
        write_results(cfg.io.output_xlsx, rows)

    success = sum(1 for r in rows if r.status == "SUCCESS")
    failed = sum(1 for r in rows if r.status == "FAILED")
    log.info("Done. success=%s failed=%s total=%s", success, failed, len(rows))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
