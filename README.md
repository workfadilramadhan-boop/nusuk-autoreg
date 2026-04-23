# Nusuk Auto-Registration Bot

Bot untuk auto-registrasi akun di aplikasi **Nusuk** (International Visitor) yang berjalan di emulator **MEmu**, baca data dari file Excel, dan auto-ambil OTP via **mail.tm**.

- ✏️ **Input**: Excel (passport, visa, DOB, phone, dll — satu baris = satu akun)
- 📱 **Target**: aplikasi Nusuk di emulator MEmu Android (via ADB + uiautomator2)
- 📧 **OTP**: otomatis via mail.tm (email temporer)
- 📊 **Output**: Excel berisi status per akun + email yang dipakai

> **Penting.** Bot ini untuk keperluan legit (mis. travel agent meregistrasikan akun jamaah asli dengan data paspor/visa asli). Gunakan dengan tanggung jawab, hormati ToS Nusuk.

---

## 1. Prasyarat (Windows)

1. **Python 3.10+** — download di https://www.python.org/downloads/ (waktu install centang *Add Python to PATH*).
2. **MEmu Play** — download di https://www.memuplay.com/.
3. **ADB (Android Debug Bridge)** — biasanya sudah bundled di `C:\Program Files\Microvirt\MEmu\adb.exe`. Kalau belum ada, install [Android platform-tools](https://developer.android.com/studio/releases/platform-tools).
4. **Aplikasi Nusuk** — install di dalam MEmu (cari "Nusuk" di Play Store emulator).

Lihat [scripts/setup_windows.md](scripts/setup_windows.md) untuk langkah lengkap.

---

## 2. Install

```bat
git clone https://github.com/workfadilramadhan-boop/nusuk-autoreg.git
cd nusuk-autoreg

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Pertama kali uiautomator2 butuh push agent ke device:

```bat
python -m uiautomator2 init
```

---

## 3. Konfigurasi

Copy template config:

```bat
copy config.example.yaml config.yaml
```

Edit `config.yaml` — yang paling penting:

```yaml
adb:
  host: "127.0.0.1"
  port: 21503                                 # lihat MEmu Multi-Instance Manager
  adb_path: "C:/Program Files/Microvirt/MEmu/adb.exe"

nusuk:
  package: "sa.gov.mcit.hajj"                 # pastikan package name benar
```

**Cara cek port ADB MEmu:** buka *MEmu Multi-Instance Manager* → lihat kolom *ADB* di samping instance kamu. Instance pertama biasanya `21503`, berikutnya `21513`, `21523`, dst.

**Cara cek package name Nusuk:** di MEmu, jalankan Nusuk, lalu di PowerShell:

```bat
adb -s 127.0.0.1:21503 shell dumpsys window windows ^| findstr mFocusedApp
```

Atau lewat ADB:

```bat
adb -s 127.0.0.1:21503 shell pm list packages ^| findstr -i nusuk
```

---

## 4. Siapkan data Excel

Template ada di [`data/input_template.xlsx`](data/input_template.xlsx).

| Kolom | Wajib? | Catatan |
|---|---|---|
| `first_name` | ✅ | |
| `last_name` | ✅ | |
| `passport_no` | ✅ | nomor paspor |
| `visa_no` | ✅ | nomor visa Saudi |
| `date_of_birth` | ✅ | `YYYY-MM-DD` atau `DD/MM/YYYY` |
| `phone_indo` | ✅ | boleh `+62…`, `08…`, atau `8…` — bot normalize |
| `password` | ⬜ | opsional, kalau kosong bot generate (8+ char, upper/lower/digit/special) |
| `email` | — | diisi bot (alamat mail.tm) |
| `email_password` | — | diisi bot (password mailbox) |
| `status` | — | `PENDING` / `SUCCESS` / `FAILED` |
| `error` | — | isi pesan error kalau FAILED |
| `account_created_at` | — | timestamp UTC saat sukses |

Copy `data/input_template.xlsx` → `data/input.xlsx`, lalu isi data kamu.

---

## 5. Jalankan

```bat
.venv\Scripts\activate
python -m src.main --config config.yaml
```

Flag berguna:
- `--input data/input.xlsx` override input
- `--output output/results.xlsx` override output
- `--limit 3` proses 3 akun aja (buat test dulu)
- `--dry-run` cuma validasi Excel, gak buka emulator
- `--verbose` log level DEBUG

Progress & status:
- Log ditulis ke `output/logs/run-YYYYmmdd-HHMMSS.log`.
- Excel output di-update **setelah tiap row** — aman kalau kamu stop di tengah jalan, tinggal jalankan lagi, bot akan skip yang `status == SUCCESS`.
- Kalau ada error, bot nyimpan screenshot di `output/screenshots/row0001-attempt1.png`.

---

## 6. Flow Nusuk yang diotomasi

Langkah diturunkan dari video tutorial [Cara Daftar di Aplikasi Nusuk – Insomnia Project](https://www.youtube.com/watch?v=I00Tn2dX1sM):

1. Buka Nusuk → izinkan permission.
2. Ganti bahasa ke *English*.
3. *Create account* → *International visitor*.
4. Pilih negara **Indonesia**.
5. Input **Passport Number** → *Continue*.
6. Pilih **Visa** → input **Visa Number** → *Continue*.
7. Input **Date of Birth** → *Continue* × 2 → *Yes*.
8. Buat **Password** (8+ char, upper+lower+digit+special) → centang → *Continue*.
9. Input **Phone Number** Indonesia → *Continue*.
10. Input **Email** (dari mail.tm) → *Continue*.
11. Tunggu **OTP** di email → bot poll mail.tm → auto-input → *Verify*.
12. Location → *Continue*.
13. Privacy → centang → *Confirm and continue*.

---

## 7. Troubleshooting

**`adb connect` gagal / device offline**
- Pastikan MEmu jalan dan sudah fully booted.
- Coba restart ADB: `adb kill-server && adb start-server`.
- Cek port di MEmu Multi-Instance Manager.

**`Element not found: Create account`**
- Kemungkinan UI Nusuk beda locale / beda versi. Jalankan dengan `--verbose`, bot akan dump `output/screenshots/*.png` + print hierarchy di log.
- Edit label di `src/nusuk_flow.py` (constant `SEL`).

**OTP tidak masuk**
- mail.tm kadang delay 30-60 detik. Naikkan `mailtm.otp_timeout_sec` di config.
- Cek inbox manual dengan kredensial di `output/results.xlsx` (kolom `email` + `email_password`) di https://mail.tm/.

**Bot klik kecepatan / typo di input**
- Naikkan `nusuk.action_delay` di config (default 0.8 detik).

---

## 8. Struktur project

```
nusuk-autoreg/
├── config.example.yaml
├── data/
│   └── input_template.xlsx
├── output/                     # dibuat saat runtime
│   ├── logs/
│   ├── screenshots/
│   └── results.xlsx
├── requirements.txt
├── scripts/
│   ├── generate_template.py
│   └── setup_windows.md
├── src/
│   ├── adb.py                  # wrapper uiautomator2 + ADB
│   ├── config.py               # load config YAML
│   ├── excel_io.py             # baca/tulis Excel
│   ├── mailtm.py               # client mail.tm (create, poll OTP)
│   ├── main.py                 # CLI entrypoint
│   ├── nusuk_flow.py           # 14 step registrasi Nusuk
│   └── utils.py                # password gen, phone/date normalize, logging
└── tests/
    └── test_utils.py
```

---

## 9. Disclaimer

Script ini disediakan apa adanya. Pastikan penggunaan sesuai dengan [Terms of Service Nusuk](https://www.nusuk.sa/) dan regulasi lokal. Data paspor/visa adalah data sensitif — **jangan commit file `data/input.xlsx` ke repo publik**.
