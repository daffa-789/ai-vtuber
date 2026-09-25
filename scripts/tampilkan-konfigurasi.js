// Tampilkan konfigurasi avatar yang AKAN dipakai, dibaca dari .env lewat parser
// yang sama dengan browser. Berguna sebelum menyalahkan model atau kode:
//
//   node scripts/tampilkan-konfigurasi.js          -- tabel ringkas
//   node scripts/tampilkan-konfigurasi.js --env    -- blok .env siap tempel
import { readFileSync } from 'node:fs';
import { basename } from 'node:path';
import { envDariDisk } from './env.js';
import { bacaKonfigurasi, blokEnv } from '../web/konfigurasi.js';

const konfig = bacaKonfigurasi(envDariDisk());
const mentah = (() => {
  try {
    return readFileSync('.env', 'utf8');
  } catch {
    return '';
  }
})();

const baris = (e) => {
  const resep = e.lapisan.map((l) => `${l.id}=${l.nilai}${l.blend === 'Add' ? '' : `:${l.blend}`}`).join(' ');
  return `  ${e.nama.padEnd(16)} ${String(e.lapisan.length).padStart(2)} parameter  ${
    e.dariEnv ? 'dari .env' : 'bawaan   '
  }  ${resep}`;
};

console.log(`\nModel     : ${konfig.modelUrl}`);
console.log(`Render    : skala=${konfig.render.skala ?? 'auto'} maks=${konfig.render.skalaMaks} antialias=${konfig.render.halus}`);
console.log(`Panggung  : ${konfig.panggung.ukuran}${konfig.panggung.lebar ? ` (lebar ${konfig.panggung.lebar})` : ''}${konfig.panggung.tinggi ? ` (tinggi ${konfig.panggung.tinggi})` : ''}`);
console.log(`Avatar    : zoom=${konfig.avatar.zoom} x=${konfig.avatar.x} jangkar=${konfig.avatar.jangkar}`);
console.log(`Gerakan   : kedip=${konfig.kedip} napas=${konfig.napas} kursor=${konfig.ikutiKursor} pudar=${konfig.pudarDetik}s`);
console.log(
  `Irama     : jedaSaatSembunyi=${konfig.irama.jedaSaatSembunyi} fpsSaatTakFokus=${konfig.irama.fpsSaatTakFokus || 'penuh'}`,
);
console.log(`Dasar     : ${konfig.ekspresiDasar}${konfig.awalPose.length ? ` + pose ${konfig.awalPose.join(' ')}` : ''}`);
console.log(`.env      : ${mentah ? basename('.env') + ' terpakai' : 'KOSONG (semua bawaan)'}`);

console.log('\nWajah (tag chat):');
for (const e of konfig.wajah) console.log(baris(e));
console.log('\nPose (kanal [prop:nama], ditumpuk di atas wajah):');
for (const e of konfig.pose) console.log(baris(e));
console.log('\nGerakan:');
for (const g of konfig.gerakan) console.log(`  ${g.nama.padEnd(16)} grup=${g.grup} berkas=${g.berkas}${g.sumber ? ` sumber=${g.sumber}` : ''} ulang=${g.ulang}`);

if (konfig.peringatan.length) {
  console.log(`\nPERINGATAN (${konfig.peringatan.length}):`);
  for (const p of konfig.peringatan) console.log(`  - ${p}`);
} else {
  console.log('\ntidak ada peringatan sintaks');
}

if (process.argv.includes('--env')) {
  console.log('\n--- blok .env siap tempel ---\n');
  console.log(blokEnv(konfig));
}
