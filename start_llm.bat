@echo off
setlocal
REM ==========================================================================
REM  HuoHuo - Launcher "Otak" LLM lokal (llama-server, OpenAI-compatible)
REM  Jalan di http://127.0.0.1:8080  (dipakai huohuo.config.llama_endpoint)
REM
REM  Semua bisa ditimpa lewat environment, jadi tidak perlu menyunting berkas
REM  ini untuk bereksperimen. Contoh:
REM      set VTUBER_LLAMA_CTX=2048 && start_llm.bat
REM
REM  CATATAN MESIN INI: tidak ada GPU diskrit (hanya Intel Iris Xe). Build yang
REM  terpasang di tools\llama.cpp adalah build CPU, jadi -ngl 0 bukan kelalaian:
REM  memang tidak ada jalur GPU pada binary itu. Bobot model tetap duduk di RAM
REM  bersama yang sama walau pakai Vulkan, jadi offload GPU tidak menambah
REM  memori -- hanya menambah kecepatan.
REM ==========================================================================

set "BASE=%~dp0"

REM --- lokasi binary (CPU = bawaan; isi dengan folder build Vulkan untuk coba)
if not defined VTUBER_LLAMA_DIR set "VTUBER_LLAMA_DIR=%BASE%tools\llama.cpp"
set "LLAMA=%VTUBER_LLAMA_DIR%\llama-server.exe"

REM --- model
set "MODEL=%BASE%model\Qwen3.5-4B-Deckard-HERETIC-UNCENSORED-Thinking.Q4_K_M.gguf"
if defined VTUBER_LLAMA_MODEL set "MODEL=%VTUBER_LLAMA_MODEL%"

REM --- parameter. Bawaan SAMA seperti sebelum launcher ini diparameterkan,
REM     supaya tidak ada perubahan perilaku yang tidak disengaja.
REM     ctx 2048 memangkas KV cache dan membebaskan RAM, tapi riwayat panjang
REM     bisa terpotong -- turunkan sendiri hanya kalau RAM sedang sesak.
if not defined VTUBER_LLAMA_CTX     set "VTUBER_LLAMA_CTX=4096"
if not defined VTUBER_LLAMA_THREADS set "VTUBER_LLAMA_THREADS=4"
if not defined VTUBER_LLAMA_NGL     set "VTUBER_LLAMA_NGL=0"
if not defined VTUBER_LLAMA_PORT    set "VTUBER_LLAMA_PORT=8080"

if not exist "%LLAMA%" (
    echo [HuoHuo] GAK KETEMU llama-server.exe di: %LLAMA%
    echo          Download dulu binari llama.cpp Windows CPU ke folder tools\llama.cpp
    pause
    exit /b 1
)
if not exist "%MODEL%" (
    echo [HuoHuo] GAK KETEMU model GGUF di: %MODEL%
    pause
    exit /b 1
)

echo [HuoHuo] Menyalakan otak LLM di http://127.0.0.1:%VTUBER_LLAMA_PORT% ...
echo          binary : %LLAMA%
echo          ctx    : %VTUBER_LLAMA_CTX%   ngl: %VTUBER_LLAMA_NGL%   threads: %VTUBER_LLAMA_THREADS%
echo          Tunggu sampai muncul "listening", lalu buka jendela HuoHuo.
echo          Tutup jendela ini untuk mematikan otak.
echo.

"%LLAMA%" -m "%MODEL%" -ngl %VTUBER_LLAMA_NGL% -c %VTUBER_LLAMA_CTX% -ctk q8_0 -ctv q8_0 --reasoning off -t %VTUBER_LLAMA_THREADS% --host 127.0.0.1 --port %VTUBER_LLAMA_PORT%

endlocal
