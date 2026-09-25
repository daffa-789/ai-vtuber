// @ts-check
/**
 * Satu-satunya tempat konfigurasi avatar dibaca: wajah, pose, gerakan, dan
 * ukuran gambar. Semuanya boleh ditimpa dari .env, jadi tidak ada lagi resep
 * yang cuma hidup di kepala atau di ujung skrip.
 *
 * Browser memanggil bacaKonfigurasi(import.meta.env), skrip Node memanggil
 * bacaKonfigurasi(process.env) -- kedua-duanya record string yang sama, dan
 * skrip perkakas di scripts/ memuat .env sendiri (scripts/env.js).
 *
 * Aturan penulisan di .env
 *   VITE_WAJAH_<NAMA>   resep ekspresi wajah  -> token `Id=Nilai` dipisah spasi
 *   VITE_POSE_<NAMA>    resep pose/aksesoris  -> bentuk token sama
 *   VITE_GERAK_<NAMA>   satu berkas motion    -> token `grup=... berkas=... ulang=false`
 *   Nama kunci = nama setelah prefiks: huruf besar jadi kecil, garis bawah jadi
 *   garis hubung. VITE_POSE_PAMER_BARANG_1 -> "pamer-barang-1".
 *   Blend default `Add` (menambah di atas nilai bawaan parameter). Tulis
 *   `Id=Nilai:Overwrite` untuk menulis mentah, atau :Multiply untuk mengali.
 *   Nilai negatif boleh: ParamEyeLOpen=-0.35.
 *
 * Kata setelah VITE_WAJAH_ / VITE_POSE_ SELALU dianggap nama ekspresi, jadi
 * knob lain memakai awalan sendiri (VITE_EKSPRESI_DASAR, VITE_AWAL_POSE) supaya
 * tidak menabrak. Itu juga alasan `awal` tidak bisa dipakai sebagai nama pose.
 *
 * Nilai yang tidak ditulis di .env memakai bawaan di berkas ini -- bawaannya
 * sengaja sama persis dengan hasil pemasangan model tanggal 2026-09-24, supaya
 * clone baru tanpa .env tetap menampilkan karakter yang sama.
 */

const PREFIKS = {
  wajah: 'VITE_WAJAH_',
  pose: 'VITE_POSE_',
  gerak: 'VITE_GERAK_',
};

/** Resep sembilan wajah yang dipetakan ke tag di persona.md. */
export const WAJAH_BAWAAN = {
  netral: '',
  senyum:
    'ParamMouthForm=1 ParamEyeLSmile=1 ParamEyeRSmile=1 ParamEyeLOpen=-0.35 ParamEyeROpen=-0.35 ParamBrowLY=0.2',
  semangat:
    'Param59=30 ParamMouthForm=1 ParamEyeLSmile=0.6 ParamEyeRSmile=0.6 ParamEyeLOpen=0.2 ParamEyeROpen=0.2 ParamBrowLY=0.5',
  kaget: 'ParamEyeLOpen=0.4 ParamEyeROpen=0.4 ParamBrowLY=1 ParamMouthForm=-0.6 Param50=0.7',
  bingung: 'Param69=30 ParamMouthForm=-0.4 ParamBrowLForm=-0.5 ParamBrowLY=-0.4',
  lelah: 'ParamEyeLOpen=-0.7 ParamEyeROpen=-0.7 ParamBrowLY=-0.5 ParamBrowLForm=-0.6 ParamMouthForm=-0.3',
  goda: 'Param60=30 ParamMouthForm=0.8 ParamEyeLOpen=-0.3 ParamEyeROpen=-0.3 ParamEyeLSmile=0.7 ParamEyeRSmile=0.7',
  sebal: 'Param67=30 ParamBrowLForm=-0.879 ParamBrowLY=-0.727',
  sedih: 'Param68=30 ParamBrowLForm=1 ParamBrowLY=-0.788',
};

/**
 * Tujuh lapisan model yang bukan wajah: topi, tongkat, kacamata, hantu, tangan
 * memeluk, dan dua kali memamerkan barang. Dipisah dari `wajah` karena mereka
 * ditumpuk DI ATAS emosi, bukan menggantikannya -- lihat LapisanPose di main.ts.
 */
export const POSE_BAWAAN = {
  'tanpa-topi': 'Param71=30',
  tongkat: 'Param72=30',
  kacamata: 'Param66=30',
  'hantu-kecil': 'Param64=30',
  'tangan-memeluk': 'Param65=30',
  'pamer-barang-1': 'Param61=30',
  'pamer-barang-2': 'Param62=30',
};

export const GERAK_BAWAAN = {
  'sedih-melambai':
    'grup=isyarat berkas=gerakan/sedih-melambai.motion3.json sumber=Scene1.motion3.json ulang=false',
};

/** Bawaan lama: resolution = min(devicePixelRatio, 2), kanvas min(90vh,100%). */
export const RENDER_BAWAAN = {
  VITE_MODEL_URL: '/models/penyihir/penyihir.model3.json',
  VITE_RENDER_SKALA: 'auto',
  VITE_RENDER_SKALA_MAKS: '8',
  VITE_RENDER_HALUS: 'true',
  VITE_PANGGUNG_UKURAN: 'min(90vh, 100%)',
  VITE_PANGGUNG_LEBAR: '',
  VITE_PANGGUNG_TINGGI: '',
  VITE_AVATAR_ZOOM: '0.96',
  VITE_AVATAR_X: '0.5',
  VITE_AVATAR_JANGKAR: '1',
  VITE_EKSPRESI_DASAR: 'netral',
  VITE_PUDAR_WAJAH_MS: '1000',
  VITE_KEDIP: 'true',
  VITE_NAPAS: 'true',
  VITE_IKUTI_KURSOR: 'true',
  VITE_AWAL_POSE: '',
  VITE_TEKSTUR: '8192',
  VITE_IRAMA_JEDA_SAAT_SEMBUNYI: 'true',
  VITE_IRAMA_FPS_SAAT_TAK_FOKUS: '30',
};

const BLEND = new Set(['Add', 'Multiply', 'Overwrite']);

/**
 * @typedef {{ id: string, nilai: number, blend: string }} Lapisan
 * @typedef {{ nama: string, dariEnv: boolean, lapisan: Lapisan[] }} Ekspresi
 * @typedef {{ nama: string, dariEnv: boolean, grup: string, berkas: string, sumber: string, ulang: boolean }} Gerakan
 * @typedef {{
 *   modelUrl: string, wajah: Ekspresi[], pose: Ekspresi[], gerakan: Gerakan[],
 *   ekspresiDasar: string, awalPose: string[], pudarDetik: number,
 *   kedip: boolean, napas: boolean, ikutiKursor: boolean, tekstur: string,
 *   render: { skala: number | null, skalaMaks: number, halus: boolean },
 *   irama: { jedaSaatSembunyi: boolean, fpsSaatTakFokus: number },
 *   panggung: { ukuran: string, lebar: string, tinggi: string },
 *   avatar: { zoom: number, x: number, jangkar: number },
 *   peringatan: string[],
 * }} Konfigurasi
 */

/**
 * Kunci -> nama ekspresi. `VITE_POSE_PAMER_BARANG_1` -> `pamer-barang-1`.
 * @param {string} kunci
 * @param {string} prefiks
 */
export function namaDariKunci(kunci, prefiks) {
  return kunci.slice(prefiks.length).toLowerCase().replace(/_/g, '-');
}

/**
 * Nama ekspresi -> kunci .env, untuk menulis blok konfigurasi dan untuk
 * memberi tahu user baris mana yang harus dia sunting.
 * @param {string} nama
 * @param {string} prefiks
 */
export function kunciDariNama(nama, prefiks) {
  return prefiks + nama.replace(/-/g, '_').toUpperCase();
}

const ANGKA = /^-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?$/;

/**
 * Uraikan token `Id=Nilai[:Blend]`. Daftar token dipecah pada spasi dan koma
 * supaya kedua-duanya nyaman ditulis tangan.
 *
 * @param {string} teks
 * @param {string} nama untuk awalan pesan peringatan
 * @param {string[]} peringatan
 * @returns {Lapisan[]}
 */
function uraiLapisan(teks, nama, peringatan) {
  // Kosongkan sebuah resep dengan kata "kosong": baris kosong (KEY=) tidak
  // dijamin bertahan -- Node membuang nilai kosong dari --env-file, jadi
  // "hapus resep" dan "lupa menulis resep" tidak bisa dibedakan di sana.
  if (/^(kosong|none|empty)$/i.test(teks.trim())) return [];
  /** @type {Lapisan[]} */
  const lapisan = [];
  for (const t of teks.split(/[\s,]+/).filter(Boolean)) {
    const i = t.indexOf('=');
    if (i === -1) {
      peringatan.push(`${nama}: token "${t}" tidak berbentuk Id=Nilai`);
      continue;
    }
    const id = t.slice(0, i).trim();
    const [mentahNilai, mentahBlend] = t.slice(i + 1).split(':');
    if (!ANGKA.test(mentahNilai.trim())) {
      peringatan.push(`${nama}: nilai "${mentahNilai}" untuk ${id} bukan angka`);
      continue;
    }
    let blend = 'Add';
    if (mentahBlend) {
      // Huruf besar-kecil berkas exp3.json sensitif: 'add' bukan 'Add'.
      const cocok = [...BLEND].find((b) => b.toLowerCase() === mentahBlend.trim().toLowerCase());
      if (!cocok) {
        peringatan.push(`${nama}: blend "${mentahBlend}" tidak ada (Add / Multiply / Overwrite)`);
        continue;
      }
      blend = cocok;
    }
    const duplikat = lapisan.find((l) => l.id === id && l.blend === blend);
    if (duplikat) {
      peringatan.push(`${nama}: ${id} ditulis dua kali, nilai terakhir yang dipakai`);
      duplikat.nilai = Number(mentahNilai);
      continue;
    }
    lapisan.push({ id, nilai: Number(mentahNilai), blend });
  }
  return lapisan;
}

/**
 * Uraikan token `grup=... berkas=... sumber=... ulang=false` untuk satu motion.
 * `berkas` adalah path di DALAM folder model (tempat dia dipasang); `sumber`
 * nama berkas aslinya di folder mentah, kalau berbeda dari `berkas`.
 *
 * @param {string} teks
 * @param {string} nama
 * @param {string[]} peringatan
 * @returns {{grup: string, berkas: string, sumber: string, ulang: boolean}}
 */
function uraiGerak(teks, nama, peringatan) {
  /** @type {{grup: string, berkas: string, sumber: string, ulang: boolean}} */
  const gerak = { grup: '', berkas: '', sumber: '', ulang: false };
  for (const t of teks.split(/[\s,]+/).filter(Boolean)) {
    const i = t.indexOf('=');
    const k = i === -1 ? t : t.slice(0, i);
    const v = i === -1 ? '' : t.slice(i + 1);
    if (k === 'grup' || k === 'berkas' || k === 'sumber') {
      gerak[k] = v;
    } else if (k === 'ulang') {
      gerak.ulang = v === 'true' || v === '1';
    } else {
      peringatan.push(`${nama}: token gerakan tidak dikenal "${t}" (pakai grup= berkas= sumber= ulang=)`);
    }
  }
  if (!gerak.berkas) peringatan.push(`${nama}: VITE_GERAK_ tanpa berkas= jadi tidak dipasang`);
  return gerak;
}

/**
 * Kumpulkan semua nama dari env + bawaan, urutan: bawaan dulu (supaya tombol
 * tetap stabil), lalu nama baru dari .env.
 * @param {Record<string, string>} env
 * @param {string} prefiks
 * @param {Record<string, string>} bawaan
 * @returns {[string, {teks: string, dariEnv: boolean}][]}
 */
function kumpulkan(env, prefiks, bawaan) {
  /** @type {Map<string, {teks: string, dariEnv: boolean}>} */
  const hasil = new Map();
  for (const [nama, teks] of Object.entries(bawaan)) hasil.set(nama, { teks, dariEnv: false });

  for (const kunci of Object.keys(env).sort()) {
    if (!kunci.startsWith(prefiks) || kunci.length === prefiks.length) continue;
    const nama = namaDariKunci(kunci, prefiks);
    hasil.set(nama, { teks: env[kunci] ?? '', dariEnv: true });
  }
  return [...hasil.entries()];
}

/**
 * @param {Record<string, string | undefined>} [env]
 * @returns {Konfigurasi}
 */
export function bacaKonfigurasi(env = {}) {
  /** @type {Record<string, string>} */
  const bersih = {};
  for (const [k, v] of Object.entries(env)) if (typeof v === 'string') bersih[k] = v;

  /** @type {string[]} */
  const peringatan = [];
  /** @type {(kunci: string, defaultnya: number) => number} */
  const angka = (kunci, defaultnya) => {
    const mentah = bersih[kunci];
    if (mentah === undefined || mentah.trim() === '') return defaultnya;
    const n = Number(mentah);
    if (!Number.isFinite(n)) {
      peringatan.push(`${kunci}="${mentah}" bukan angka, pakai ${defaultnya}`);
      return defaultnya;
    }
    return n;
  };
  /** @type {(kunci: string, defaultnya: boolean) => boolean} */
  const bool = (kunci, defaultnya) => {
    const mentah = bersih[kunci];
    if (mentah === undefined || mentah.trim() === '') return defaultnya;
    if (/^(true|1|ya|on)$/i.test(mentah.trim())) return true;
    if (/^(false|0|tidak|off)$/i.test(mentah.trim())) return false;
    peringatan.push(`${kunci}="${mentah}" tidak dikenal, pakai ${defaultnya}`);
    return defaultnya;
  };

  /**
   * @param {string} prefiks
   * @param {Record<string, string>} bawaan
   * @returns {Ekspresi[]}
   */
  const bangun = (prefiks, bawaan) =>
    kumpulkan(bersih, prefiks, bawaan).map(([nama, { teks, dariEnv }]) => ({
      nama,
      dariEnv,
      lapisan: uraiLapisan(teks, nama, peringatan),
    }));

  const wajah = bangun(PREFIKS.wajah, WAJAH_BAWAAN);
  const pose = bangun(PREFIKS.pose, POSE_BAWAAN);
  /** @type {Gerakan[]} */
  const gerakan = kumpulkan(bersih, PREFIKS.gerak, GERAK_BAWAAN)
    .map(([nama, { teks, dariEnv }]) => ({ nama, dariEnv, ...uraiGerak(teks, nama, peringatan) }))
    .filter((g) => g.berkas);

  const ekspresiDasar = bersih.VITE_EKSPRESI_DASAR?.trim() || RENDER_BAWAAN.VITE_EKSPRESI_DASAR;
  if (!wajah.some((w) => w.nama === ekspresiDasar)) {
    peringatan.push(
      `VITE_EKSPRESI_DASAR="${ekspresiDasar}" tidak ada di daftar wajah, pakai "${wajah[0]?.nama ?? 'netral'}"`,
    );
  }

  const skalaMentah = (bersih.VITE_RENDER_SKALA ?? 'auto').trim();
  const skala = skalaMentah === '' || /^auto$/i.test(skalaMentah) ? null : Number(skalaMentah);
  if (skala !== null && !Number.isFinite(skala)) {
    peringatan.push(`VITE_RENDER_SKALA="${skalaMentah}" bukan angka, kembali ke auto`);
  }

  /** @type {(kunci: string, defaultnya: string) => string} */
  const teks = (kunci, defaultnya) => {
    const mentah = bersih[kunci];
    return mentah === undefined || mentah.trim() === '' ? defaultnya : mentah.trim();
  };

  const konfig = {
    modelUrl: teks('VITE_MODEL_URL', RENDER_BAWAAN.VITE_MODEL_URL),
    wajah,
    pose,
    gerakan,
    ekspresiDasar: wajah.some((w) => w.nama === ekspresiDasar)
      ? ekspresiDasar
      : (wajah[0]?.nama ?? 'netral'),
    awalPose: (bersih.VITE_AWAL_POSE ?? '').split(/[\s,]+/).filter(Boolean),
    pudarDetik: Math.max(0, angka('VITE_PUDAR_WAJAH_MS', 1000)) / 1000,
    kedip: bool('VITE_KEDIP', true),
    napas: bool('VITE_NAPAS', true),
    ikutiKursor: bool('VITE_IKUTI_KURSOR', true),
    tekstur: (bersih.VITE_TEKSTUR ?? RENDER_BAWAAN.VITE_TEKSTUR).trim(),
    render: {
      skala: skala !== null && Number.isFinite(skala) && skala > 0 ? skala : null,
      skalaMaks: Math.max(0.5, angka('VITE_RENDER_SKALA_MAKS', Number(RENDER_BAWAAN.VITE_RENDER_SKALA_MAKS))),
      halus: bool('VITE_RENDER_HALUS', true),
    },
    irama: {
      jedaSaatSembunyi: bool('VITE_IRAMA_JEDA_SAAT_SEMBUNYI', true),
      fpsSaatTakFokus: angka('VITE_IRAMA_FPS_SAAT_TAK_FOKUS', 30),
    },
    panggung: {
      ukuran: teks('VITE_PANGGUNG_UKURAN', RENDER_BAWAAN.VITE_PANGGUNG_UKURAN),
      lebar: teks('VITE_PANGGUNG_LEBAR', ''),
      tinggi: teks('VITE_PANGGUNG_TINGGI', ''),
    },
    avatar: {
      zoom: angka('VITE_AVATAR_ZOOM', 0.96),
      x: angka('VITE_AVATAR_X', 0.5),
      jangkar: angka('VITE_AVATAR_JANGKAR', 1),
    },
    peringatan,
  };

  for (const p of konfig.awalPose) {
    if (!pose.some((x) => x.nama === p)) {
      peringatan.push(`VITE_AWAL_POSE: "${p}" bukan nama pose (daftar VITE_POSE_ ...)`);
    }
  }
  if (konfig.irama.fpsSaatTakFokus < 0) {
    peringatan.push(
      `VITE_IRAMA_FPS_SAAT_TAK_FOKUS=${konfig.irama.fpsSaatTakFokus} negatif, dianggap 0 (tidak dibatasi)`,
    );
  }
  return /** @type {Konfigurasi} */ (konfig);
}

/**
 * Bentuk berkas exp3.json dari satu resep. Dipakai browser (untuk menyuntik
 * ekspresi tanpa menulis berkas) DAN scripts/pasang-model.js (untuk menulis
 * berkasnya), jadi format ekspresi tidak mungkin beda di dua tempat.
 * @param {Ekspresi} e
 * @param {number} pudarDetik
 */
export function ekspresiKeJson(e, pudarDetik) {
  return {
    Type: 'Live2D Expression',
    FadeInTime: pudarDetik,
    FadeOutTime: pudarDetik,
    Parameters: e.lapisan.map((l) => ({ Id: l.id, Value: l.nilai, Blend: l.blend })),
  };
}

/**
 * Cek resep terhadap tabel parameter model yang SEDANG berjalan. Rentang tiap
 * parameter model ini tidak seragam (lapisan ekspresi 0..30, ParamEyeLOpen
 * 0..1.4), jadi menebak dari kepala pernah salah dua kali.
 *
 * @param {ReturnType<typeof bacaKonfigurasi>} konfig
 * @param {{ids: string[], defaultValues: ArrayLike<number>, minimumValues: ArrayLike<number>, maximumValues: ArrayLike<number>}} tabel
 */
export function periksaTerhadapModel(konfig, tabel) {
  /** @type {string[]} */
  const keluar = [];
  /** @type {Map<string, number>} */
  const indeks = new Map();
  tabel.ids.forEach((id, i) => indeks.set(id, i));

  /** @type {[jenis: string, daftar: Ekspresi[]][]} */
  const kumpulan = [
    ['wajah', konfig.wajah],
    ['pose', konfig.pose],
  ];
  for (const [jenis, daftar] of kumpulan) {
    for (const e of daftar) {
      for (const l of e.lapisan) {
        const i = indeks.get(l.id);
        if (i === undefined) {
          keluar.push(`${jenis} "${e.nama}": parameter ${l.id} tidak ada di model`);
          continue;
        }
        const min = tabel.minimumValues[i];
        const maks = tabel.maximumValues[i];
        const dasar = tabel.defaultValues[i];
        // Add menulis DI ATAS nilai bawaan, jadi yang harus dicek hasil akhirnya.
        const target = l.blend === 'Add' ? dasar + l.nilai : l.nilai;
        const eps = 1e-6;
        if (target < min - eps || target > maks + eps) {
          keluar.push(
            `${jenis} "${e.nama}": ${l.id} ${l.nilai} (${l.blend}) jadi ${target.toFixed(3)}, di luar rentang model ${min}..${maks}`,
          );
        }
      }
    }
  }

  return keluar;
}

/**
 * Blok .env siap tempel dari konfigurasi efektif -- ini yang dipakai untuk
 * menulis .env.example, jadi dokumen dan bawaan tidak bisa saling menjauh.
 * @param {ReturnType<typeof bacaKonfigurasi>} konfig
 */
export function blokEnv(konfig) {
  /** @type {string[]} */
  const baris = [];
  /** @param {string} v */
  const petik = (v) => (v === '' ? '' : `"${v}"`);
  /**
   * @param {Ekspresi[]} daftar
   * @param {string} prefiks
   */
  const tulis = (daftar, prefiks) => {
    for (const e of daftar) {
      const teks = e.lapisan.map((l) => `${l.id}=${l.nilai}${l.blend === 'Add' ? '' : `:${l.blend}`}`).join(' ');
      // "kosong" ditulis eksplisit: baris KEY= dengan nilai kosong tidak selalu
      // bertahan sampai ke parser.
      baris.push(`${kunciDariNama(e.nama, prefiks)}=${petik(teks || 'kosong')}`);
    }
  };
  baris.push('# ---- ukuran gambar & ketajaman ----');
  baris.push(`VITE_MODEL_URL=${petik(konfig.modelUrl)}`);
  baris.push(
    `VITE_RENDER_SKALA=${petik(konfig.render.skala === null ? 'auto' : String(konfig.render.skala))}`,
  );
  baris.push(`VITE_RENDER_SKALA_MAKS=${petik(String(konfig.render.skalaMaks))}`);
  baris.push(`VITE_RENDER_HALUS=${petik(String(konfig.render.halus))}`);
  baris.push(`VITE_PANGGUNG_UKURAN=${petik(konfig.panggung.ukuran)}`);
  baris.push(`VITE_PANGGUNG_LEBAR=${petik(konfig.panggung.lebar)}`);
  baris.push(`VITE_PANGGUNG_TINGGI=${petik(konfig.panggung.tinggi)}`);
  baris.push(`VITE_AVATAR_ZOOM=${petik(String(konfig.avatar.zoom))}`);
  baris.push(`VITE_AVATAR_X=${petik(String(konfig.avatar.x))}`);
  baris.push(`VITE_AVATAR_JANGKAR=${petik(String(konfig.avatar.jangkar))}`);
  baris.push(`VITE_KEDIP=${petik(String(konfig.kedip))}`);
  baris.push(`VITE_NAPAS=${petik(String(konfig.napas))}`);
  baris.push(`VITE_IKUTI_KURSOR=${petik(String(konfig.ikutiKursor))}`);
  baris.push(`VITE_TEKSTUR=${petik(konfig.tekstur)}`);
  baris.push('');
  baris.push('# ---- irama render (hemat GPU saat avatar tidak dilihat) ----');
  baris.push('# Jeda = berhenti menggambar sama sekali saat tab latar / jendela diminimakan.');
  baris.push('# fpsSaatTakFokus = batas FPS saat jendela terlihat tapi tidak fokus; 0 = penuh.');
  baris.push(`VITE_IRAMA_JEDA_SAAT_SEMBUNYI=${petik(String(konfig.irama.jedaSaatSembunyi))}`);
  baris.push(`VITE_IRAMA_FPS_SAAT_TAK_FOKUS=${petik(String(konfig.irama.fpsSaatTakFokus))}`);
  baris.push('');
  baris.push('# ---- wajah (tag chat) ----');
  baris.push(`VITE_EKSPRESI_DASAR=${petik(konfig.ekspresiDasar)}`);
  baris.push(`VITE_PUDAR_WAJAH_MS=${petik(String(Math.round(konfig.pudarDetik * 1000)))}`);
  tulis(konfig.wajah, PREFIKS.wajah);
  baris.push('');
  baris.push('# ---- pose & aksesoris (kanal [prop:nama], ditumpuk di atas wajah) ----');
  baris.push(`VITE_AWAL_POSE=${petik(konfig.awalPose.join(' '))}`);
  tulis(konfig.pose, PREFIKS.pose);
  baris.push('');
  baris.push('# ---- gerakan ----');
  for (const g of konfig.gerakan) {
    const token = [`grup=${g.grup}`, `berkas=${g.berkas}`];
    if (g.sumber) token.push(`sumber=${g.sumber}`);
    token.push(`ulang=${g.ulang}`);
    baris.push(`${kunciDariNama(g.nama, PREFIKS.gerak)}=${petik(token.join(' '))}`);
  }
  return baris.join('\n');
}
