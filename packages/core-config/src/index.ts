import type { EnvSource } from './coerce.ts'
import { angka, angkaFloat, bool_, daftar, nilai } from './coerce.ts'
import { AKAR, bacaEnvAkar, temukanPersona } from './paths.ts'

/**
 * Konfigurasi sisi server — port `server_py/konfig.py`.
 *
 * ATURAN: setiap kunci dan nilai bawaan dipertahankan verbatim. Kalau sebuah
 * kunci hilang dari sini, perilaku aplikasi berubah tanpa pesan — kelas bug yang
 * sudah beberapa kali terjadi di proyek lama. Tambahkan kunci baru, jangan
 * ringkas yang ada.
 */

export interface EkspresiWajah { nama: string }
export interface Pose { nama: string }
export interface Gerak {
  nama: string
  grup: string
  indeks: number
  ulang: boolean
}

export interface Konfig {
  akar: string
  akarPersona: string
  warnings: string[]

  // ── wujud aplikasi ──
  port: number
  tampak: 'pet' | 'browser'
  petSembunyi: 'tidak' | 'layar-penuh' | 'maksimal'
  petTray: boolean
  petHotkey: string

  // ── otak percakapan ──
  llmProvider: 'local' | 'llama_cpp' | 'vulkan' | 'ollama'
  localModelPath: string
  localModelThreads: number
  localModelCtx: number
  /** Nama yang dilaporkan `/v1/chat/completions`; kosong = turun dari nama berkas. */
  localModelAlias: string
  /**
   * min_p untuk llama-server. WAJIB 0 untuk MiniCPM5: bawaan llama.cpp 0,05
   * membuat model ini mengulang kalimat (peringatan eksplisit OpenBMB).
   */
  localMinP: number
  localTopP: number
  /**
   * `-rea` llama-server. MiniCPM5 punya mode berpikir; kalau hidup, balasan
   * diawali blok <think> sehingga `bacaTagAwal()` gagal menemukan tag emosi.
   */
  localReasoning: 'on' | 'off' | 'auto'
  llamaServer: string
  vulkanNgl: number
  vulkanFa: boolean
  vulkanCtx: number
  vulkanPerangkat: string
  vulkanMuatBoot: boolean
  vulkanSlotDiam: boolean
  ollamaUrl: string
  ollamaModel: string

  // ── STT ──
  sttHidup: boolean
  sttModel: string
  sttModelPath: string
  sttBahasa: string
  sttKomputasi: string
  sttThreads: number
  sttBeam: number
  sttMuatBoot: boolean
  sttMaksDetik: number

  jedaFakta: number

  // ── rantai suara ──
  ttsRantai: string[]
  ttsBatasaDetik: number
  ttsJedaResep: number
  ttsPerKalimat: boolean

  // ── piper ──
  piperModel: string
  piperSuara: string
  piperVolume: number
  piperPanjang: number
  piperNoise: number
  piperNoiseW: number

  // ── rvc ──
  rvcHidup: boolean
  rvcFolder: string
  rvcModel: string
  rvcIndeks: string
  rvcVersi: string
  rvcF0: string
  rvcTranspose: number
  rvcIndeksLaju: number
  rvcProteksi: number
  rvcPencucian: number
  rvcCampurRms: number
  rvcResample: number
  rvcMuatBoot: boolean
  rvcBatasAntrean: number

  // ── cache ──
  ttsCache: boolean
  ttsCacheFolder: string
  ttsCacheMaksMb: number
  ttsMeterik: boolean

  // ── avatar (dari VITE_*) ──
  wajah: EkspresiWajah[]
  pose: Pose[]
  gerak: Gerak[]

  // ── tiruan & batas ──
  stub: boolean
  maksPesan: number
  maksKarakter: number
  maksBody: number
  maksAudio: number
}

/** Bangun `EnvSource` dari berkas `.env` akar + `process.env`. */
export function buatEnvSource(
  akar: string = AKAR,
  environ: Record<string, string | undefined> = process.env,
): EnvSource {
  return { file: bacaEnvAkar(akar), environ, warnings: [] }
}

/**
 * Parse daftar `VITE_WAJAH_*` / `VITE_POSE_*` / `VITE_GERAK_*` dari `.env`.
 *
 * Padanan blok terakhir `konfig.py`. `indeks` gerak dihitung dari posisi kurva
 * yang cocok di `public/models/silverwolf/gerakan/<berkas>`; kalau berkasnya
 * belum ada (aset Live2D gitignored), indeks jatuh ke 0 — sama seperti Python.
 */
export function parseAvatar(
  env: EnvSource,
  akar: string,
  bacaMotionIndeks: (berkas: string) => number,
): Pick<Konfig, 'wajah' | 'pose' | 'gerak'> {
  const wajah: EkspresiWajah[] = []
  const pose: Pose[] = []
  const gerak: Gerak[] = []

  const semua: Array<[string, string]> = [
    ...Object.entries(env.file),
    ...Object.entries(env.environ).filter((e): e is [string, string] => typeof e[1] === 'string'),
  ]

  for (const [k, v] of semua) {
    if (k.startsWith('VITE_WAJAH_'))
      wajah.push({ nama: k.replace('VITE_WAJAH_', '').toLowerCase().replace(/_/g, '-') })
    else if (k.startsWith('VITE_POSE_'))
      pose.push({ nama: k.replace('VITE_POSE_', '').toLowerCase().replace(/_/g, '-') })
    else if (k.startsWith('VITE_GERAK_')) {
      const pasangan = [...v.matchAll(/(\S+)=([^\s]+)/g)]
      const ambil = (nama: string) => pasangan.find(m => m[1] === nama)?.[2] ?? ''
      const berkas = ambil('berkas')
      gerak.push({
        nama: k.replace('VITE_GERAK_', '').toLowerCase(),
        grup: ambil('grup'),
        indeks: berkas ? bacaMotionIndeks(berkas) : 0,
        ulang: v.includes('ulang=true') || v.includes('ulang=1'),
      })
    }
  }

  void akar
  return { wajah, pose, gerak }
}

/** Bangun konfigurasi lengkap dari sebuah `EnvSource`. */
export function bacaKonfig(
  env: EnvSource = buatEnvSource(),
  akar: string = AKAR,
  bacaMotionIndeks: (berkas: string) => number = () => 0,
): Konfig {
  const tampakMentah = nilai(env, 'VTUBER_TAMPAK', 'pet').toLowerCase()
  const sembunyiMentah = nilai(env, 'VTUBER_PET_SEMBUNYI', 'layar-penuh').toLowerCase()
  const providerMentah = nilai(env, 'VTUBER_LLM_PROVIDER', 'local').toLowerCase()

  const localModelCtx = angka(env, 'VTUBER_LOCAL_MODEL_CTX', 8192)

  const konfig: Konfig = {
    akar,
    akarPersona: temukanPersona(akar),
    warnings: env.warnings,

    port: angka(env, 'VTUBER_PORT', 8787),
    tampak: tampakMentah === 'browser' ? 'browser' : 'pet',
    petSembunyi:
      sembunyiMentah === 'tidak' || sembunyiMentah === 'maksimal' ? sembunyiMentah : 'layar-penuh',
    petTray: bool_(env, 'VTUBER_PET_TRAY', true),
    petHotkey: nilai(env, 'VTUBER_PET_HOTKEY', 'ctrl+shift+s').toLowerCase(),

    llmProvider: (['local', 'llama_cpp', 'vulkan', 'ollama'].includes(providerMentah)
      ? providerMentah
      : 'local') as Konfig['llmProvider'],
    localModelPath: nilai(env, 'VTUBER_LOCAL_MODEL_PATH', ''),
    localModelThreads: angka(env, 'VTUBER_LOCAL_MODEL_THREADS', 4),
    localModelCtx,
    localModelAlias: nilai(env, 'VTUBER_LOCAL_MODEL_ALIAS', ''),
    localMinP: angkaFloat(env, 'VTUBER_LOCAL_MIN_P', 0),
    localTopP: angkaFloat(env, 'VTUBER_LOCAL_TOP_P', 0.95),
    localReasoning: (['on', 'off', 'auto'].includes(nilai(env, 'VTUBER_LOCAL_REASONING', 'off').toLowerCase())
      ? nilai(env, 'VTUBER_LOCAL_REASONING', 'off').toLowerCase()
      : 'off') as Konfig['localReasoning'],
    llamaServer: nilai(env, 'VTUBER_LLAMA_SERVER', 'bin/llama'),
    vulkanNgl: angka(env, 'VTUBER_VULKAN_NGL', 99),
    vulkanFa: bool_(env, 'VTUBER_VULKAN_FA', true),
    // `angka(...) or LOCAL_MODEL_CTX`: 0 berarti "ikut konteks model lokal".
    vulkanCtx: angka(env, 'VTUBER_VULKAN_CTX', 0) || localModelCtx,
    vulkanPerangkat: nilai(env, 'VTUBER_VULKAN_PERANGKAT', 'Vulkan0'),
    vulkanMuatBoot: bool_(env, 'VTUBER_VULKAN_MUAT_BOOT', true),
    vulkanSlotDiam: bool_(env, 'VTUBER_VULKAN_SLOT_DIAM', true),
    ollamaUrl: nilai(env, 'VTUBER_OLLAMA_URL', 'http://127.0.0.1:11434'),
    ollamaModel: nilai(env, 'VTUBER_OLLAMA_MODEL', 'llama3.2:3b'),

    sttHidup: bool_(env, 'VTUBER_STT', true),
    sttModel: nilai(env, 'VTUBER_STT_MODEL', 'base'),
    sttModelPath: nilai(env, 'VTUBER_STT_MODEL_PATH', 'aset/suara/whisper'),
    sttBahasa: nilai(env, 'VTUBER_STT_BAHASA', 'id'),
    sttKomputasi: nilai(env, 'VTUBER_STT_KOMPUTASI', 'int8'),
    sttThreads: angka(env, 'VTUBER_STT_THREADS', 2),
    sttBeam: angka(env, 'VTUBER_STT_BEAM', 1),
    sttMuatBoot: bool_(env, 'VTUBER_STT_MUAT_BOOT', false),
    sttMaksDetik: angka(env, 'VTUBER_STT_MAKS_DETIK', 30),

    jedaFakta: angka(env, 'VTUBER_JEDA_FAKTA', 8),

    ttsRantai: daftar(env, 'VTUBER_TTS_RANTAI', 'piper+rvc,piper'),
    ttsBatasaDetik: angka(env, 'VTUBER_TTS_BATAS_DETIK', 20),
    ttsJedaResep: angka(env, 'VTUBER_TTS_JEDA_RESEP', 60),
    ttsPerKalimat: bool_(env, 'VTUBER_TTS_PER_KALIMAT', true),

    piperModel: nilai(env, 'VTUBER_TTS_PIPER_MODEL', 'aset/suara/piper/id_ID-news_tts-medium.onnx'),
    piperSuara: nilai(env, 'VTUBER_TTS_PIPER_SUARA', 'id_ID-news_tts-medium'),
    piperVolume: angka(env, 'VTUBER_TTS_PIPER_VOLUME', 100),
    piperPanjang: angkaFloat(env, 'VTUBER_TTS_PIPER_PANJANG', 1.0),
    piperNoise: angkaFloat(env, 'VTUBER_TTS_PIPER_NOISE', 0.667),
    piperNoiseW: angkaFloat(env, 'VTUBER_TTS_PIPER_NOISE_W', 0.8),

    rvcHidup: bool_(env, 'VTUBER_RVC', true),
    rvcFolder: nilai(env, 'VTUBER_RVC_FOLDER', 'aset/suara/rvc'),
    rvcModel: nilai(env, 'VTUBER_RVC_MODEL', 'furina'),
    rvcIndeks: nilai(env, 'VTUBER_RVC_INDEKS', ''),
    rvcVersi: nilai(env, 'VTUBER_RVC_VERSI', 'v2'),
    rvcF0: nilai(env, 'VTUBER_RVC_F0', 'pm'),
    rvcTranspose: angka(env, 'VTUBER_RVC_TRANSPOSE', 0),
    rvcIndeksLaju: angkaFloat(env, 'VTUBER_RVC_INDEKS_LAJU', 0.0),
    rvcProteksi: angkaFloat(env, 'VTUBER_RVC_PROTEKSI', 0.33),
    rvcPencucian: angka(env, 'VTUBER_RVC_PENCUCIAN', 3),
    rvcCampurRms: angkaFloat(env, 'VTUBER_RVC_CAMPUR_RMS', 1.0),
    rvcResample: angka(env, 'VTUBER_RVC_RESAMPLE', 0),
    rvcMuatBoot: bool_(env, 'VTUBER_RVC_MUAT_BOOT', false),
    rvcBatasAntrean: angka(env, 'VTUBER_RVC_BATAS_ANTREAN', 8),

    ttsCache: bool_(env, 'VTUBER_TTS_CACHE', true),
    ttsCacheFolder: nilai(env, 'VTUBER_TTS_CACHE_FOLDER', 'var/cache-suara'),
    ttsCacheMaksMb: angka(env, 'VTUBER_TTS_CACHE_MAKS_MB', 250),
    ttsMeterik: bool_(env, 'VTUBER_TTS_METERIK', false),

    ...parseAvatar(env, akar, bacaMotionIndeks),

    stub: bool_(env, 'VTUBER_STUB', false),
    maksPesan: 24,
    maksKarakter: 4000,
    maksBody: 64 * 1024,
    maksAudio: 2 * 1024 * 1024,
  }

  return konfig
}

let _cache: Konfig | undefined

/** Konfigurasi proses ini (dibuat sekali, lalu di-cache). */
export function konfig(): Konfig {
  _cache ??= bacaKonfig()
  return _cache
}

export { AKAR, AKAR_PERSONA, bacaEnvAkar, dariAkar, temukanPersona } from './paths.ts'
export { angka, angkaFloat, bool_, daftar, nilai } from './coerce.ts'
export type { EnvSource } from './coerce.ts'
export { bacaEnv, bersih, potongKomentar } from './env-file.ts'
