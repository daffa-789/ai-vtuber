@echo off
cd /d "%~dp0"
echo Menghidupkan Silver Wolf (mode web)...
echo.
echo Peramban terbuka sendiri setelah servernya siap (10-15 dtk saat GPU dipanaskan).
echo Tekan Ctrl+C di jendela ini jika ingin menghentikan.
echo.
echo Mau jendela melayang di desktop? jalankan: .venv\Scripts\python.exe main.py --pet
echo.
.venv\Scripts\python.exe main.py
pause
