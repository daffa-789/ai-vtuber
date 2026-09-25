// Muat .env sendiri.
//
// Dulu flag `--env-file-if-exists=.env` di package.json yang mengurus ini. Setelah
// package.json dihapus, `node scripts/pasang-model.js` tetap jalan TAPI tidak melihat
// satu pun kunci VITE_ (terukur: 0 tanpa flag, 34 dengan flag) sehingga semua resep di
// .env diabaikan diam-diam dan yang tertulis ke berkas adalah nilai bawaan.
//
// Variabel lingkungan asli menang atas .env, sama seperti yang dilakukan Vite.
import { readFileSync } from 'node:fs';

export function envDariDisk(jalur = '.env') {
  const hasil = {};
  let mentah = '';
  try {
    mentah = readFileSync(jalur, 'utf8');
  } catch {
    return { ...process.env };
  }

  for (const baris of mentah.split(/\r?\n/)) {
    const t = baris.trim();
    if (!t || t.startsWith('#') || !t.includes('=')) continue;
    const kunci = t.slice(0, t.indexOf('=')).trim();
    let nilai = t.slice(t.indexOf('=') + 1).trim();
    if (
      nilai.length > 1 &&
      ((nilai.startsWith('"') && nilai.endsWith('"')) || (nilai.startsWith("'") && nilai.endsWith("'")))
    ) {
      nilai = nilai.slice(1, -1);
    }
    hasil[kunci] = nilai;
  }
  return { ...hasil, ...process.env };
}
