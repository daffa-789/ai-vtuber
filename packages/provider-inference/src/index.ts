/**
 * Tipe bersama untuk seluruh provider (Brain / Ears / Mouth / Body).
 *
 * Semua nama tipe di sini adalah padanan langsung dari struktur Python lama,
 * supaya peta migrasi di rencana (§3) bisa ditelusuri satu per satu.
 */

/** Peran pesan yang dikenal jalur LLM. Sama dengan yang diterima `/api/chat`. */
export type ChatRole = 'system' | 'user' | 'assistant'

export interface ChatMessage {
  role: ChatRole
  content: string
}

/** Opsi generasi; semuanya opsional supaya provider boleh mengabaikan. */
export interface GenerateOptions {
  maxTokens?: number
  temperature?: number
  /** Batas waktu absolut (epoch ms). Provider harus berhenti melewati ini. */
  deadline?: number
  signal?: AbortSignal
}

/**
 * WAV PCM16 mono yang dipegang di memori — bentuk kanonik audio di seluruh
 * pipeline (padanan `bytes` di `server_py/wav.py`).
 */
export interface WavBytes {
  /** Data WAV lengkap termasuk header RIFF. */
  readonly bytes: Uint8Array
  /** Laju sampel menurut header. */
  readonly sampleRate: number
  /** Jumlah kanal menurut header. */
  readonly channels: number
}

/** Hasil transkripsi; `mesin` dipakai `/api/stt` untuk melaporkan mesin aktif. */
export interface Transcript {
  teks: string
  mesin: string
}

/** Alasan ketersediaan, dipakai untuk banner/health tanpa melempar error. */
export interface Availability {
  ok: boolean
  reason: string
}

/**
 * BRAIN — penyedia LLM.
 *
 * Tiga jalur lama (`model_lokal`, `model_vulkan`, `ollama_client`) runtuh jadi
 * dua: `llama-server` (CPU *dan* Vulkan, hanya beda `-ngl`) dan `ollama`.
 * Keduanya bicara protokol OpenAI-compatible `/v1`, jadi `xsai` bisa memimpin.
 */
export interface LlmProvider {
  readonly id: 'llama-server' | 'ollama'
  available(): Promise<Availability>
  /** Stream potongan teks mentah (termasuk tag `[senyum]` di awal). */
  stream(messages: ChatMessage[], options?: GenerateOptions): AsyncIterable<string>
  dispose(): Promise<void>
}

/**
 * EARS — penyedia ASR. Tetap di sidecar Node (faster-whisper / whisper.cpp).
 */
export interface AsrProvider {
  readonly id: string
  available(): Promise<Availability>
  transcribe(wav: ArrayBuffer, opts?: { language?: string; deadline?: number }): Promise<Transcript>
  dispose(): Promise<void>
}

/**
 * MOUTH — penyedia TTS. `fingerprint()` masuk ke cache key rantai suara;
 * kalau berubah, cache lama otomatis tidak dipakai (kelas bug yang dulu
 * diperbaiki di `tts_rvc.py` lewat iterasi `param_aktif()`).
 */
export interface TtsProvider {
  readonly id: 'piper'
  available(): Promise<Availability>
  fingerprint(): Promise<string>
  synthesize(text: string, deadline: number): Promise<WavBytes>
  dispose(): Promise<void>
}

/**
 * Tahap pengubah audio (WAV → WAV). RVC adalah *stage*, bukan TtsProvider,
 * karena ia butuh audio sumber dan tidak bisa berdiri sendiri.
 */
export interface AudioStage {
  readonly id: 'rvc'
  readonly input: 'wav'
  readonly output: 'wav'
  available(): Promise<Availability>
  fingerprint(): Promise<string>
  run(wav: WavBytes, remainingMs: number): Promise<WavBytes>
  dispose(): Promise<void>
}

/**
 * BODY — renderer karakter. Implementasi Live2D ada di
 * `@silverwolf/stage-ui-live2d`; antarmuka ini menjaga `stage-ui` tidak
 * bergantung pada PIXI/Cubism secara langsung.
 */
export interface StageRenderer {
  load(url: string): Promise<void>
  setExpression(name: string): void
  setPose(name: string, on: boolean): void
  startMotion(group: string, index: number, priority: number): Promise<boolean>
  setMouth(level: number): void
  destroy(): void
}
