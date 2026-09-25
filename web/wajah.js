// Mesin wajah: mengubah resep di .env menjadi ekspresi Live2D yang benar-benar
// berjalan, plus lapisan pose yang bisa ditumpuk di atas ekspresi itu.
//
// Kenapa disuntik saat runtime dan bukan dibaca dari berkas ekspresi saja:
// supaya nilai bisa dityetel di .env, halaman dimuat ulang, dan hasilnya
// langsung terlihat -- tanpa menjalankan ulang pemasangan model.
import { ekspresiKeJson, periksaTerhadapModel } from './konfigurasi.mjs';
import { setelan } from './setelan.js';

/**
 * Tabel parameter model yang sedang berjalan. Rentang tiap parameter di model
 * ini TIDAK seragam (lapisan ekspresi 0..30, ParamEyeLOpen 0..1.4, rahang
 * 0..1), jadi nilai batas dibaca dari sini, tidak pernah ditebak.
 */
export function tabelParameter(inti) {
  const p = inti.getModel().parameters;
  const ada = p.minimumValues && p.maximumValues;
  if (!ada) console.warn('Cubism core tidak memberi rentang parameter; nilai tidak dijepit');
  return {
    indeks: new Map(p.ids.map((id, i) => [id, i])),
    ids: p.ids,
    default: p.defaultValues,
    min: p.minimumValues ?? p.defaultValues,
    maks: p.maximumValues ?? p.defaultValues,
    ada: !!ada,
  };
}

/**
 * Ganti (atau tambahkan) definisi ekspresi pada model dengan resep dari .env.
 * `expressions[i]` yang sudah terisi membuat pustaka melewati unduhan berkas
 * sama sekali, jadi berkas ekspresi di disk hanya dipakai alat luar
 * (VTube Studio / Cubism Editor) hasil pemasangan model.
 */
export function suntikEkspresi(model, konfig) {
  const manager = model.internalModel.motionManager.expressionManager;
  if (!manager) {
    konfig.peringatan.push('model ini tidak punya expression manager; ekspresi .env dilewati');
    return [];
  }
  manager.definitions ??= [];
  manager.expressions ??= [];

  const dipasang = [];
  for (const e of [...konfig.wajah, ...konfig.pose]) {
    let i = manager.definitions.findIndex((d) => (d.Name ?? '') === e.nama);
    if (i === -1) {
      manager.definitions.push({ Name: e.nama });
      i = manager.definitions.length - 1;
    } else {
      // Nama sama tapi berkas lama: buang File agar tidak pernah di-fetch lagi.
      delete manager.definitions[i].File;
    }
    manager.expressions[i] = manager.createExpression(
      ekspresiKeJson(e, konfig.pudarDetik),
      manager.definitions[i],
    );
    dipasang.push(e.nama);
  }
  return dipasang;
}

/**
 * Pose/aksesoris sebagai lapisan parameter yang menulis PALING AKHIR
 * (event beforeModelUpdate), jadi ia tidak ditimpa ekspresi, kedip, fokus,
 * fisika, maupun motion -- dan bisa tampil bersamaan dengan wajah apa pun.
 * Nilainya dilembutkan ke target supaya topi tidak muncul dengan sentakan.
 */
export class LapisanPose {
  hidup = new Set();
  target = new Map();
  kini = new Map();
  terakhir = performance.now();

  constructor(inti, tabel, daftar, pudarDetik) {
    this.inti = inti;
    this.tabel = tabel;
    this.daftar = daftar;
    this.pudarDetik = pudarDetik;
  }

  nilaiAbsolut(l) {
    const i = this.tabel.indeks.get(l.id);
    if (i === undefined) return 0;
    const dasar = this.tabel.default[i];
    const target =
      l.blend === 'Overwrite' ? l.nilai : l.blend === 'Multiply' ? dasar * l.nilai : dasar + l.nilai;
    return this.tabel.ada ? Math.min(this.tabel.maks[i], Math.max(this.tabel.min[i], target)) : target;
  }

  /** Susun ulang target dari sekumpulan pose yang sedang aktif. */
  hitung() {
    const berikut = new Map();
    for (const e of this.daftar) {
      if (!this.hidup.has(e.nama)) continue;
      for (const l of e.lapisan) {
        const i = this.tabel.indeks.get(l.id);
        if (i === undefined) continue;
        berikut.set(l.id, this.nilaiAbsolut(l));
      }
    }
    // Pose yang dimatikan harus kembali ke nilai bawaan, bukan berhenti di tengah.
    for (const id of [...this.target.keys(), ...berikut.keys()]) {
      if (!berikut.has(id)) {
        const i = this.tabel.indeks.get(id);
        if (i !== undefined) berikut.set(id, this.tabel.default[i]);
      }
    }
    this.target = berikut;
  }

  /** @returns keadaan pose sesudah diubah, untuk menyetel tampilan tombol. */
  ubah(nama, hidup) {
    if (!this.daftar.some((e) => e.nama === nama)) {
      console.warn(`pose "${nama}" tidak ada di daftar VITE_POSE_`);
      return false;
    }
    const nyala = hidup ?? !this.hidup.has(nama);
    if (nyala) this.hidup.add(nama);
    else this.hidup.delete(nama);
    this.hitung();
    return nyala;
  }

  aktif(nama) {
    return this.hidup.has(nama);
  }

  get nyala() {
    return [...this.hidup];
  }

  /** Jalan tiap frame, SESUDAH fisika dan pose Cubism ditulis -- lihat urutan update(). */
  perFrame() {
    const sekarang = performance.now();
    const dt = Math.min(0.25, (sekarang - this.terakhir) / 1000);
    this.terakhir = sekarang;
    // Mendekat secara eksponensial: konstanta waktu = pudarDetik, jadi 0 = langsung.
    const laju = this.pudarDetik > 0 ? 1 - Math.exp(-dt / this.pudarDetik) : 1;

    for (const [id, tujuan] of this.target) {
      const punya = this.kini.get(id) ?? this.asli(id);
      const nilai = Math.abs(tujuan - punya) < 1e-4 ? tujuan : punya + (tujuan - punya) * laju;
      this.kini.set(id, nilai);
      if (nilai === tujuan && this.hidup.size === 0) {
        // Semua pose mati dan sudah pulang: jangan tulis terus, biar motion bebas.
        this.kini.delete(id);
        this.target.delete(id);
      }
      this.inti.setParameterValueById(id, nilai);
    }
  }

  asli(id) {
    const i = this.tabel.indeks.get(id);
    return i === undefined ? 0 : this.tabel.default[i];
  }
}

/** Semua keluhan konfigurasi: sintaks dari parser + kecocokan dengan model nyata. */
export function peringatanKonfigurasi(inti) {
  const keluar = [...setelan.peringatan];
  try {
    const p = inti.getModel().parameters;
    keluar.push(
      ...periksaTerhadapModel(setelan, {
        ids: p.ids,
        defaultValues: p.defaultValues,
        minimumValues: p.minimumValues ?? [],
        maximumValues: p.maximumValues ?? [],
      }),
    );
  } catch (err) {
    keluar.push(`parameter model tidak terbaca: ${err instanceof Error ? err.message : String(err)}`);
  }
  return keluar;
}
