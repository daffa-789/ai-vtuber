import { potongKalimat } from "./kalimat.js";
class AntreanSuara {
  opsi;
  antrean = [];
  sisa = "";
  ditutup = false;
  berjalan = false;
  berhentiTotal = false;
  tunggu = [];
  audio;
  konteks;
  bingkai;
  constructor(opsi) {
    this.opsi = opsi;
  }
  /** Tambah potongan teks dari aliran; kalimat utuh langsung masuk antrean. */
  tambah(potongan) {
    if (this.berhentiTotal || !potongan) return;
    this.sisa += potongan;
    const { kalimat, sisa } = potongKalimat(this.sisa);
    this.sisa = sisa;
    for (const k of kalimat) this.antrean.push(k);
    void this.jalankan();
  }
  /** Aliran selesai: sisa tanpa penutup kalimat tetap diucapkan. */
  tutup() {
    if (this.berhentiTotal) return;
    const sisa = this.sisa.trim();
    if (sisa) {
      this.antrean.push(sisa);
      this.sisa = "";
    }
    this.ditutup = true;
    void this.jalankan();
  }
  /** Tunggu sampai seluruh antrean habis diputar. */
  async tungguSelesai() {
    if (this.berhentiTotal) return;
    if (this.ditutup && !this.antrean.length && !this.berjalan) return;
    await new Promise((resolve) => this.tunggu.push(resolve));
  }
  /** Hentikan semua: audio sekarang, antrean, dan gerakan mulut. */
  berhenti() {
    this.berhentiTotal = true;
    this.antrean.length = 0;
    this.sisa = "";
    if (this.bingkai !== void 0) cancelAnimationFrame(this.bingkai);
    this.bingkai = void 0;
    this.opsi.onMulut?.(0);
    if (this.audio) {
      this.audio.pause();
      this.audio = void 0;
    }
    this.selesaikanSemua();
  }
  selesaikanSemua() {
    const daftar = this.tunggu;
    this.tunggu = [];
    for (const r of daftar) r();
  }
  async jalankan() {
    if (this.berjalan || this.berhentiTotal) return;
    this.berjalan = true;
    try {
      while (this.antrean.length && !this.berhentiTotal) {
        const teks = this.antrean.shift();
        this.opsi.onKalimatMulai?.(teks);
        try {
          const blob = await this.opsi.synthesize(teks);
          if (this.berhentiTotal) break;
          await this.putar(blob);
        } catch (error) {
          this.opsi.onGalat?.(error);
        }
        this.opsi.onKalimatSelesai?.(teks);
      }
    } finally {
      this.berjalan = false;
      if (this.ditutup && !this.antrean.length) this.selesaikanSemua();
    }
  }
  async putar(blob) {
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    this.audio = audio;
    const konteks = this.konteksAudio();
    let sumber;
    let analyser;
    if (konteks) {
      try {
        sumber = konteks.createMediaElementSource(audio);
        analyser = konteks.createAnalyser();
        analyser.fftSize = 1024;
        analyser.smoothingTimeConstant = 0.2;
        sumber.connect(analyser);
        analyser.connect(konteks.destination);
      } catch {
        sumber = void 0;
        analyser = void 0;
      }
    }
    try {
      await audio.play();
      if (analyser) this.gerakkanMulut(analyser);
      await new Promise((resolve) => {
        audio.onended = () => resolve();
        audio.onerror = () => resolve();
      });
    } finally {
      if (this.bingkai !== void 0) cancelAnimationFrame(this.bingkai);
      this.bingkai = void 0;
      this.opsi.onMulut?.(0);
      sumber?.disconnect();
      analyser?.disconnect();
      URL.revokeObjectURL(url);
      if (this.audio === audio) this.audio = void 0;
    }
  }
  konteksAudio() {
    try {
      this.konteks ??= new AudioContext();
      if (this.konteks.state === "suspended") void this.konteks.resume();
      return this.konteks;
    } catch {
      return void 0;
    }
  }
  /**
   * Ukur RMS dan kirim ke `onMulut`. Serangan cepat, pelepasan lambat —
   * supaya mulut tidak berkedut di setiap jeda antar-kata.
   */
  gerakkanMulut(analyser) {
    const data = new Uint8Array(analyser.fftSize);
    let halus = 0;
    const langkah = () => {
      if (this.berhentiTotal) return;
      analyser.getByteTimeDomainData(data);
      let jumlah = 0;
      for (let i = 0; i < data.length; i++) {
        const s = (data[i] - 128) / 128;
        jumlah += s * s;
      }
      const rms = Math.sqrt(jumlah / data.length);
      const target = Math.min(1, rms * 5);
      halus = target > halus ? target : halus * 0.82 + target * 0.18;
      this.opsi.onMulut?.(halus);
      this.bingkai = requestAnimationFrame(langkah);
    };
    this.bingkai = requestAnimationFrame(langkah);
  }
}
export {
  AntreanSuara
};
