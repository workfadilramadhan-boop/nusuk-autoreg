# Setup lengkap di Windows

## 1. Install Python 3.10+
1. Download installer di https://www.python.org/downloads/windows/.
2. Saat install, **centang** `Add Python to PATH`.
3. Verifikasi di PowerShell:
   ```powershell
   python --version
   pip --version
   ```

## 2. Install MEmu Play
1. Download di https://www.memuplay.com/.
2. Install & buka. Biarkan ia boot sampai home screen Android.
3. Di setting MEmu, disarankan:
   - Resolusi: 720×1280 (portrait) — UI mobile app lebih stabil.
   - Root: ON (optional, beberapa app butuh).
   - Android version: 9 atau di atasnya kalau tersedia.

## 3. Verifikasi ADB
ADB bundled MEmu biasanya di:
```
C:\Program Files\Microvirt\MEmu\adb.exe
```

Tambahkan ke PATH, atau isi absolute path di `config.yaml` field `adb.adb_path`.

Coba connect:
```powershell
adb connect 127.0.0.1:21503
adb devices
```

Expected output:
```
List of devices attached
127.0.0.1:21503 device
```

Port ADB untuk tiap instance MEmu bisa dilihat di **MEmu Multi-Instance Manager** kolom *ADB*. Default instance pertama = `21503`.

## 4. Install Nusuk di MEmu
1. Di MEmu, buka **Play Store** (sign in akun Google).
2. Cari `Nusuk`, install.
3. Buka sekali lalu tutup — ini mempersiapkan app folder.

## 5. Setup uiautomator2 agent
Pertama kali pakai, push agent ke device:
```powershell
cd nusuk-autoreg
.venv\Scripts\activate
python -m uiautomator2 init
```

Output akhir: `success`. Kalau fail, pastikan `adb devices` menunjukkan device connected.

## 6. Cek package name Nusuk
```powershell
adb -s 127.0.0.1:21503 shell pm list packages | findstr -i nusuk
```

Copy nilai `package:xxx.yyy.zzz` (tanpa `package:`) ke `config.yaml` → `nusuk.package`.

Kalau package name yang muncul bukan `sa.gov.mcit.hajj`, update config dengan yang muncul di device kamu.

## 7. Test dry run
```powershell
python -m src.main --config config.yaml --dry-run
```

Ini cuma validasi Excel, gak sentuh emulator.

## 8. Test 1 akun dulu
Copy 1 row data ke `data/input.xlsx`, lalu:
```powershell
python -m src.main --config config.yaml --limit 1 --verbose
```

Amati log. Kalau ada step yang macet:
- Cek screenshot di `output/screenshots/`.
- Dump UI manual: `adb -s 127.0.0.1:21503 shell uiautomator dump /sdcard/ui.xml && adb -s 127.0.0.1:21503 pull /sdcard/ui.xml`.
- Sesuaikan label di `src/nusuk_flow.py` constant `SEL`.

## 9. Jalankan bulk
Setelah 1 akun sukses, isi semua data, lalu:
```powershell
python -m src.main --config config.yaml
```

Bot akan skip row yang `status == SUCCESS` — jadi aman kalau kamu interrupt & resume.
