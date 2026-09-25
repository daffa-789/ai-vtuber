// Uji pemotong kalimat: deterministik, tanpa API, tanpa browser.
// Yang dicari bukan "lulus/gagal" saja tapi berapa awal suara bisa mulai,
// diukur dari berapa karakter yang harus menunggu.
import { kalimatSiap } from '../web/kalimat.mjs';

let gagal = 0;
const sama = (label, dapat, harus) => {
  const ok = JSON.stringify(dapat) === JSON.stringify(harus);
  if (!ok) {
    gagal++;
    console.log(`BEDA  ${label}\n      dapat ${JSON.stringify(dapat)}\n      harus ${JSON.stringify(harus)}`);
  } else {
    console.log(`ok    ${label}`);
  }
};

// 1. Belum ada tanda baca -> tidak ada apa pun yang diucapkan.
sama(
  'tanpa batas, tanpa potongAwal',
  kalimatSiap('Saya Elaina, penyihir yang kebetulan tinggal di', false),
  { siap: [], sisa: 'Saya Elaina, penyihir yang kebetulan tinggal di' },
);

// 2. Kalimat selesai -> dipotong utuh.
sama(
  'kalimat selesai',
  kalimatSiap('Saya Elaina, penyihir yang kebetulan tinggal di sini. Nanti', false),
  { siap: ['Saya Elaina, penyihir yang kebetulan tinggal di sini.'], sisa: ' Nanti' },
);

// 3. Potongan awal di koma, hanya saat belum ada kalimat selesai.
sama(
  'potong di koma saat potongAwal',
  kalimatSiap('Saya Elaina, teman yang', true),
  { siap: ['Saya Elaina,'], sisa: ' teman yang' },
);

// 4. Awalan pendek (<8 karakter) tidak dipotong: satu kata bukan kalimat.
sama(
  'awalan pendek tidak dipotong',
  kalimatSiap('Ya, lanjut', true),
  { siap: [], sisa: 'Ya, lanjut' },
);

// 5. Kalau sudah ada kalimat selesai, potongAwal tidak menambah potongan kecil.
sama(
  'kalimat selesai menang atas koma',
  kalimatSiap('Sudah kelar. Nanti kita', true),
  { siap: ['Sudah kelar.'], sisa: ' Nanti kita' },
);

// 6. Aliran sungguhan: seberapa cepat potongan pertama keluar?
const JAWABAN =
  'Saya Elaina, penyihir yang kebetulan tinggal di komputer Master. ' +
  'Kamu kelihatan sibuk hari ini, jangan lupa minum.';
const sampaiPotonganPertama = (potongAwal) => {
  for (let i = 1; i <= JAWABAN.length; i++) {
    const { siap } = kalimatSiap(JAWABAN.slice(0, i), potongAwal);
    if (siap.length) return { karakter: i, potongan: siap[0] };
  }
  return { karakter: Infinity, potongan: null };
};
const lambat = sampaiPotonganPertama(false);
const cepat = sampaiPotonganPertama(true);
console.log(
  `\npotongan pertama keluar setelah ${lambat.karakter} karakter (tanpa) vs ` +
    `${cepat.karakter} karakter (dengan) -> ${Math.round((1 - cepat.karakter / lambat.karakter) * 100)}% lebih awal`,
);
console.log(`  potongan awal: ${JSON.stringify(cepat.potongan)}`);
if (cepat.karakter >= lambat.karakter) gagal++;

console.log(gagal ? `\nFAIL ${gagal} pemeriksaan` : '\nPASS pemotongan kalimat');
process.exit(gagal ? 1 : 0);
