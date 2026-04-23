"""Nusuk registration flow.

Flow ini diturunkan dari video tutorial Nusuk (Insomnia Project):
  https://www.youtube.com/watch?v=I00Tn2dX1sM

Langkah:
  1.  Buka Nusuk, izinkan permission kalau muncul.
  2.  Klik tombol language (pojok kanan atas) -> pilih English -> OK.
  3.  Tap "Create account".
  4.  Pilih "International Visitor" (opsi paling bawah).
  5.  Pilih negara: Indonesia.
  6.  Masukkan Passport Number -> Continue.
  7.  Pilih "Visa" -> masukkan Visa Number -> Continue.
  8.  Masukkan Date of Birth -> Continue -> Continue -> Yes.
  9.  Buat Password (8+ char, upper, lower, digit, special) -> centang -> Continue.
  10. Masukkan Phone Number (Indonesia) -> Continue.
  11. Masukkan Email (mail.tm) -> Continue.
  12. Tunggu OTP di email, isi OTP, Verify.
  13. Location: Continue.
  14. Privacy: centang -> Confirm and Continue.

CATATAN PENTING:
  Text label di bawah dipakai untuk `text=...` / `textContains=...` matching
  via uiautomator2. Kalau UI Nusuk beda versi / beda locale, kamu mungkin
  perlu tweak label di constant SELECTORS di bawah. Untuk debug, jalankan
  dengan flag --debug-dump biar bot simpan UI XML tiap step.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from .adb import AdbHelper
from .excel_io import AccountRow
from .mailtm import Mailbox, MailtmClient
from .utils import (
    generate_password,
    normalize_dob,
    normalize_indo_phone,
    sleep_jitter,
)

log = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Label / selector Nusuk (English locale). Ubah di sini kalau UI ganti.
# ------------------------------------------------------------------
@dataclass(frozen=True)
class Selectors:
    # Permission dialogs (Android system)
    ALLOW_BUTTON_TEXTS: tuple[str, ...] = (
        "Allow", "ALLOW",
        "Allow only while using the app",
        "While using the app",
        "Ask app not to track",
    )

    # Main landing
    CREATE_ACCOUNT: tuple[str, ...] = ("Create account", "Create Account", "CREATE ACCOUNT")
    LANGUAGE_ENGLISH: tuple[str, ...] = ("English",)
    LANGUAGE_OK: tuple[str, ...] = ("OK", "Ok", "Confirm")

    # Visitor type
    INTERNATIONAL_VISITOR: tuple[str, ...] = ("International visitor", "International Visitor")

    # Country picker
    COUNTRY_INDONESIA: tuple[str, ...] = ("Indonesia",)

    # Generic next / continue / yes buttons
    CONTINUE: tuple[str, ...] = ("Continue", "CONTINUE", "Next", "NEXT")
    YES: tuple[str, ...] = ("Yes", "YES")
    VERIFY: tuple[str, ...] = ("Verify", "VERIFY", "Confirm", "CONFIRM")
    CONFIRM_AND_CONTINUE: tuple[str, ...] = (
        "Confirm and continue", "Confirm and Continue", "Confirm & Continue",
    )

    # Visa / passport radio
    VISA_OPTION: tuple[str, ...] = ("Visa",)


SEL = Selectors()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _locators_for_texts(texts: tuple[str, ...]) -> list[dict]:
    return [{"text": t} for t in texts] + [{"textContains": t} for t in texts]


def _click_text(adb: AdbHelper, texts: tuple[str, ...], timeout: int | None = None) -> None:
    ok = adb.click_any(_locators_for_texts(texts), timeout=timeout)
    if not ok:
        raise TimeoutError(f"Tombol tidak ditemukan: {texts}")


def _click_text_if_present(
    adb: AdbHelper, texts: tuple[str, ...], timeout: int = 3
) -> bool:
    return adb.click_any(_locators_for_texts(texts), timeout=timeout)


def _dismiss_permission_dialogs(adb: AdbHelper, rounds: int = 3) -> None:
    """Ada beberapa permission prompt berturut-turut saat pertama launch."""
    for _ in range(rounds):
        clicked = _click_text_if_present(adb, SEL.ALLOW_BUTTON_TEXTS, timeout=2)
        if not clicked:
            break
        sleep_jitter(0.6)


# ------------------------------------------------------------------
# Main flow
# ------------------------------------------------------------------
def register(
    adb: AdbHelper,
    mailtm: MailtmClient,
    row: AccountRow,
    package: str,
    activity: str = "",
    otp_regex: str = r"\b(\d{4,8})\b",
    otp_timeout_sec: int = 120,
    otp_poll_interval_sec: int = 3,
) -> Mailbox:
    """Register one Nusuk account from the given row.

    Returns the mailbox used (so caller can persist the email+password).
    Raises on failure. Caller handles retries / Excel writeback.
    """
    # ---- 0. prepare data ----
    password = row.password or generate_password(12)
    row.password = password
    phone = normalize_indo_phone(row.phone_indo)
    dob_d, dob_m, dob_y = normalize_dob(row.date_of_birth)

    mailbox = mailtm.create_mailbox()
    row.email = mailbox.address
    row.email_password = mailbox.password

    # ---- 1. launch app fresh ----
    log.info("[%s %s] start Nusuk app", row.first_name, row.last_name)
    adb.clear_app(package)
    adb.start_app(package, activity)
    sleep_jitter(3.0, 0.5)
    _dismiss_permission_dialogs(adb)

    # ---- 2. set language to English ----
    # Video: tombol language di pojok kanan atas. Karena tombol itu biasanya
    # ikon tanpa text, kita cari text "English" yang muncul di list bahasa.
    # Kalau UI memunculkan list langsung, ini klik langsung.
    # Kalau perlu buka menu dulu, bot mencoba elemen dengan description/resourceId
    # umum; kalau gagal, lanjut aja — mungkin default sudah English.
    _open_language_picker(adb)
    if _click_text_if_present(adb, SEL.LANGUAGE_ENGLISH, timeout=5):
        _click_text_if_present(adb, SEL.LANGUAGE_OK, timeout=5)
        sleep_jitter(1.0)

    # ---- 3. Create account ----
    _click_text(adb, SEL.CREATE_ACCOUNT)

    # ---- 4. International visitor ----
    _click_text(adb, SEL.INTERNATIONAL_VISITOR)

    # ---- 5. Country: Indonesia ----
    _click_text(adb, SEL.COUNTRY_INDONESIA)
    _click_text_if_present(adb, SEL.CONTINUE, timeout=3)

    # ---- 6. Passport number ----
    _fill_first_edit_text(adb, row.passport_no)
    _click_text(adb, SEL.CONTINUE)

    # ---- 7. Visa -> visa number ----
    _click_text(adb, SEL.VISA_OPTION)
    _fill_first_edit_text(adb, row.visa_no)
    _click_text(adb, SEL.CONTINUE)

    # ---- 8. DOB ----
    _fill_dob(adb, dob_d, dob_m, dob_y)
    _click_text(adb, SEL.CONTINUE)
    # Video: ada dua "Continue" di sini sebelum tombol "Yes".
    _click_text_if_present(adb, SEL.CONTINUE, timeout=4)
    _click_text(adb, SEL.YES)

    # ---- 9. Password ----
    _fill_password_fields(adb, password)
    _tick_first_checkbox(adb)
    _click_text(adb, SEL.CONTINUE)

    # ---- 10. Phone number (Indonesia) ----
    _fill_first_edit_text(adb, phone)
    _click_text(adb, SEL.CONTINUE)

    # ---- 11. Email ----
    _fill_first_edit_text(adb, mailbox.address)
    _click_text(adb, SEL.CONTINUE)

    # ---- 12. OTP ----
    code = mailtm.wait_for_otp(
        mailbox,
        regex=otp_regex,
        timeout_sec=otp_timeout_sec,
        poll_interval_sec=otp_poll_interval_sec,
    )
    _fill_first_edit_text(adb, code)
    _click_text(adb, SEL.VERIFY)

    # ---- 13. Location ----
    _click_text_if_present(adb, SEL.CONTINUE, timeout=10)

    # ---- 14. Privacy ----
    _tick_first_checkbox(adb)
    if not _click_text_if_present(adb, SEL.CONFIRM_AND_CONTINUE, timeout=6):
        _click_text(adb, SEL.CONTINUE)

    # ---- 15. Wait for home screen (heuristic) ----
    time.sleep(3.0)
    log.info("Registration flow finished for %s", mailbox.address)
    return mailbox


# ------------------------------------------------------------------
# Internal UI helpers
# ------------------------------------------------------------------
def _open_language_picker(adb: AdbHelper) -> None:
    """Coba buka menu language. Kalau tombol tidak ketemu, biarkan aja —
    biasanya list bahasa langsung muncul di splash."""
    candidates = [
        {"description": "Language"},
        {"description": "Change language"},
        {"resourceIdMatches": ".*(language|lang).*"},
    ]
    for loc in candidates:
        if adb.exists(**loc):
            try:
                adb.find(**loc).click()
                time.sleep(adb.action_delay)
                return
            except Exception as e:  # noqa: BLE001
                log.debug("language picker loc failed: %s (%s)", loc, e)


def _fill_first_edit_text(adb: AdbHelper, value: str) -> None:
    field = adb.wait_for(className="android.widget.EditText")
    field.click()
    time.sleep(0.2)
    try:
        adb.dev.clear_text()
    except Exception:  # noqa: BLE001
        pass
    adb.dev.send_keys(value)
    time.sleep(adb.action_delay)


def _fill_password_fields(adb: AdbHelper, password: str) -> None:
    """Nusuk biasanya minta password + confirm password. Isi keduanya."""
    fields = adb.dev(className="android.widget.EditText")
    count = fields.count
    if count == 0:
        raise RuntimeError("Tidak menemukan field password")
    for i in range(min(count, 2)):
        f = fields[i]
        f.click()
        time.sleep(0.2)
        try:
            adb.dev.clear_text()
        except Exception:  # noqa: BLE001
            pass
        adb.dev.send_keys(password)
        time.sleep(adb.action_delay)


def _fill_dob(adb: AdbHelper, day: str, month: str, year: str) -> None:
    """Coba dua pola: (a) date picker dengan 3 EditText, (b) spinner date picker."""
    fields = adb.dev(className="android.widget.EditText")
    if fields.count >= 3:
        for f, val in zip([fields[0], fields[1], fields[2]], [day, month, year]):
            f.click()
            time.sleep(0.2)
            try:
                adb.dev.clear_text()
            except Exception:  # noqa: BLE001
                pass
            adb.dev.send_keys(val)
            time.sleep(adb.action_delay)
        return
    # Fallback: tap field tunggal & ketik "DD/MM/YYYY"
    _fill_first_edit_text(adb, f"{day}/{month}/{year}")


def _tick_first_checkbox(adb: AdbHelper) -> None:
    cb = adb.dev(className="android.widget.CheckBox")
    if cb.count == 0:
        # coba Switch sebagai fallback
        cb = adb.dev(className="android.widget.Switch")
    if cb.count == 0:
        log.warning("Tidak menemukan checkbox untuk dicentang")
        return
    first = cb[0]
    info = first.info
    if not info.get("checked"):
        first.click()
        time.sleep(adb.action_delay)
