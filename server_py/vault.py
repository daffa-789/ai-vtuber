"""Transport catatan karakter ke vault Obsidian lewat Local REST API.

Token dibaca dari ~/.qoder/settings.json (mcpServers.obsidian). Jangan pernah
memindahkannya ke .env atau ke repo.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from konfig import HOME

PANGKAL = "Waifu Memory/AI VTUBER"


def _konfig() -> dict | None:
    try:
        s = json.loads((HOME / ".qoder" / "settings.json").read_text(encoding="utf-8"))
        o = (s.get("mcpServers") or {}).get("obsidian") or {}
        auth = (o.get("headers") or {}).get("Authorization")
        if not o.get("url") or not auth:
            return None
        return {"base": urllib.parse.urlsplit(o["url"]).scheme + "://" + urllib.parse.urlsplit(o["url"]).netloc, "auth": auth}
    except (OSError, ValueError):
        return None


_K = _konfig()


def tersedia() -> bool:
    return _K is not None


def alasan_tidak_tersedia() -> str:
    return "mcpServers.obsidian tidak ditemukan di ~/.qoder/settings.json"


def _alamat(path: str) -> str:
    return f"{_K['base']}/vault/{urllib.parse.quote(path, safe='/')}"


def _unduh(path: str, metode: str = "GET", isi: str | None = None) -> tuple[int, str]:
    perm = urllib.request.Request(
        _alamat(path),
        method=metode,
        data=isi.encode("utf-8") if isi is not None else None,
        headers={
            "Authorization": _K["auth"],
            **({"Content-Type": "text/markdown"} if isi is not None else {}),
        },
    )
    try:
        with urllib.request.urlopen(perm, timeout=30) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode("utf-8", "replace")


# Links wajib ditulis: tanpa field `links`, file hasil auto-save jadi node yatim
# di graph view. `_Index` SENGAJA tidak ada di sini -- satu tautan itu menyeret
# seluruh folder waifu ke graph Qoder Memory. Lihat Waifu Memory/_PETUNJUK.md.
TAUTAN_DASAR = ["elaina-persona"]


def _tanggal() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _kerangka(nama: str, judul: str, isi: str, tautan: list[str] | None = None) -> str:
    links = list(dict.fromkeys([*TAUTAN_DASAR, *(tautan or [])]))
    baris = [
        "---",
        "type: memory",
        "kind: karakter",
        "wilayah: waifu",
        f'name: "{nama}"',
        f'description: "{judul}"',
        'project: "Desktop AI VTUBER"',
        f'updated: "{_tanggal()}"',
        "tags:",
        '  - "memory/karakter"',
        '  - "wilayah/waifu"',
        '  - "project/Desktop AI VTUBER"',
        "links:",
        *[f'  - "[[{l}]]"' for l in links],
        "---",
        "",
        f"# {judul}",
        "",
        isi.strip(),
        "",
    ]
    return "\n".join(baris)


# ── Fakta: daftar yang dia ingat tentang user.
def simpan_fakta(fakta: list[str]) -> None:
    panduan = (
        "Setiap baris di bawah masuk ke prompt sebagai sesuatu yang **dia ingat benar**.\n"
        "Aturannya: hanya yang pernah Master tulis sendiri di percakapan, atau yang\n"
        "terukur dari mesin ini. Dugaan yang belum pasti pindah ke [[Dugaan]] dan tidak boleh\n"
        "ditulis sebagai kenyataan. Selera kanonik dan preferensi lengkap dicatat di [[Preferences]],\n"
        "suasana hati di [[Mood]], dan rekaman harian di [[Riwayat]].\n\n"
    )
    isi = panduan + ("\n".join(f"- {f}" for f in fakta) if fakta else "_Belum ada fakta tersimpan._")
    _unduh(
        f"{PANGKAL}/Fakta.md",
        "PUT",
        _kerangka(
            "fakta-elaina",
            "Fakta yang Elaina ingat tentang Master",
            isi,
            ["Mood", "Quotes", "Riwayat", "Dugaan", "Preferences", "Scenario_Library", "System_Documentation", "_PETUNJUK"],
        ),
    )


def baca_fakta() -> list[str]:
    status, teks = _unduh(f"{PANGKAL}/Fakta.md")
    if status != 200:
        return []
    hasil = []
    for baris in teks.split("\n"):
        if baris.startswith("- "):
            isi = baris[2:].strip()
            if isi and not isi.startswith("_"):
                hasil.append(isi)
    return hasil


# ── Mood: state emosional, dibaca ulang tiap percakapan.
def simpan_mood(mood: dict) -> None:
    isi = "\n".join(
        x
        for x in [
            f"Valensi: {mood['valensi']:.2f} (-1 berat .. +1 senang)",
            f"Energi: {mood['energi']:.2f}",
            f"Afinitas: {mood['afinitas']:.2f} (0 jauh .. 1 dekat)",
            f"Pertukaran tercatat: {mood['pertukaran']}",
            "Terakhir diperbarui: "
            + datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            f"Alasan: {mood['alasan']}" if mood.get("alasan") else "",
        ]
        if x
    )
    _unduh(
        f"{PANGKAL}/Mood.md",
        "PUT",
        _kerangka(
            "mood-elaina",
            "Suasana hati Elaina saat ini",
            isi,
            ["Fakta", "Quotes", "Riwayat", "Preferences", "Dugaan", "Scenario_Library", "System_Documentation", "_PETUNJUK"],
        ),
    )


def baca_mood() -> dict | None:
    status, teks = _unduh(f"{PANGKAL}/Mood.md")
    if status != 200:
        return None

    def ambil(kunci: str):
        cocok = re.search(rf"{kunci}: (-?[\d.]+)", teks)
        return float(cocok.group(1)) if cocok else float("nan")

    valensi, energi, afinitas = ambil("Valensi"), ambil("Energi"), ambil("Afinitas")
    if any(v != v for v in (valensi, energi, afinitas)):  # NaN = label tidak cocok
        return None
    tertukar = re.search(r"Pertukaran tercatat: (\d+)", teks)
    return {
        "valensi": valensi,
        "energi": energi,
        "afinitas": afinitas,
        "pertukaran": int(tertukar.group(1)) if tertukar else 0,
    }


# ── Riwayat harian: satu catatan per tanggal, ditambah bukan ditimpa.
def catat_hari(baris: str) -> None:
    path = f"{PANGKAL}/Riwayat/{_tanggal()}.md"
    status, lama = _unduh(path)
    badan = [l for l in lama.split("\n") if l.startswith("- ")] if status == 200 else []
    badan.append(f"- {baris}")
    _unduh(
        path,
        "PUT",
        _kerangka(
            f"riwayat-{_tanggal()}",
            f"Riwayat percakapan {_tanggal()}",
            "\n".join(badan),
            ["Fakta", "Mood", "Quotes", "Riwayat", "Preferences", "Dugaan"],
        ),
    )
