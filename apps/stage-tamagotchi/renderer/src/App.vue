<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useCompanionStore } from '@silverwolf/stage-ui'
import { MicrophoneRecorder, WhisperTranscriber } from '@silverwolf/audio'
import { AntreanSuara, BrowserVoicePipeline } from '@silverwolf/pipelines-audio'
import { bacaTagAwal } from '@silverwolf/core-character/tags.ts'
import { bacaPanggung } from '@silverwolf/stage-ui-live2d'

const MODEL_URL = import.meta.env.VITE_MODEL_URL || '/models/silverwolf/silverwolf.model3.json'
const RVC_TRANSPOSE = Number(import.meta.env.VITE_RVC_TRANSPOSE ?? 9)
const panggung = bacaPanggung()

const store = useCompanionStore()
const input = ref(''), canvas = ref<HTMLCanvasElement>(), log = ref<HTMLElement>()
const modelState = ref<'loading' | 'ready' | 'missing'>('loading')
const recording = ref(false), audioBusy = ref(false), audioStatus = ref('')
const voiceEnabled = ref(true)
const recorder = new MicrophoneRecorder()
const whisper = new WhisperTranscriber({ language: 'indonesian', onProgress: p => { if (p.progress) audioStatus.value = `Whisper ${Math.round(p.progress)}%` } })
let voice: BrowserVoicePipeline | undefined
let antrean: AntreanSuara | undefined
let renderer: import('@silverwolf/stage-ui-live2d').Live2DRenderer | undefined

function suara(): BrowserVoicePipeline {
  voice ??= new BrowserVoicePipeline({ rvc: { contentVecUrl: '/assets/encoders/vec-768-layer-12.onnx', modelUrl: '/assets/voices/silverwolf/model.onnx', transpose: RVC_TRANSPOSE } })
  return voice
}

/**
 * Posisi awal teks yang boleh diucapkan.
 *
 * Balasan selalu diawali tag emosi `[senyum]`. Tag itu tidak boleh ikut
 * diucapkan, dan harus terdeteksi SECEPATNYA supaya raut wajah berubah di awal
 * kalimat — bukan setelah seluruh balasan rampung. `-1` = belum tahu apakah ada
 * tag (model baru menulis 1-2 karakter).
 */
function lewatiTag(teks: string): number {
  const depan = teks.replace(/^[\s`'"]*/, '')
  if (!depan) return -1
  if (depan[0] !== '[') return 0
  const tutup = depan.indexOf(']')
  if (tutup < 0) return -1
  return teks.length - depan.length + tutup + 1
}

onMounted(async () => {
  void store.checkHealth()
  if (!canvas.value) return
  try {
    const { Live2DRenderer } = await import('@silverwolf/stage-ui-live2d')
    renderer = new Live2DRenderer(canvas.value, panggung); await renderer.load(MODEL_URL); await renderer.startMotion('isyarat', 2, 1); modelState.value = 'ready'
  }
  catch (error) { console.warn('Live2D belum tersedia:', error); modelState.value = 'missing'; renderer?.destroy(); renderer = undefined }
})
onBeforeUnmount(() => { antrean?.berhenti(); renderer?.destroy(); voice?.destroy() })
watch(() => store.expression, value => renderer?.setExpression(value))
watch(() => store.messages.map(m => `${m.id}:${m.content.length}`).join(','), async () => { await nextTick(); log.value?.scrollTo({ top: log.value.scrollHeight, behavior: 'smooth' }) })
async function submit() {
  const value = input.value
  input.value = ''
  if (!voiceEnabled.value) { await store.send(value); return }

  // Hentikan sisa suara dari balasan sebelumnya sebelum memulai yang baru.
  antrean?.berhenti()

  const antrian = new AntreanSuara({
    synthesize: teks => suara().synthesize(teks),
    onMulut: level => renderer?.setMouth(level),
    onKalimatMulai: () => { audioStatus.value = 'Suara aktif' },
    onGalat: error => { audioStatus.value = error instanceof Error ? error.message : String(error) },
  })
  antrean = antrian

  let mentah = ''
  let tagSelesai = false
  let diproses = 0

  /**
   * Satu-satunya tempat teks mengalir ke antrean. Dipanggil tiap potongan
   * DAN sekali lagi di akhir, sehingga sisa tanpa penutup kalimat tetap
   * diucapkan.
   */
  const proses = (): void => {
    const pos = lewatiTag(mentah)
    if (!tagSelesai) {
      if (pos < 0) return // tag belum lengkap — tunggu potongan berikutnya
      tagSelesai = true
      // Raut wajah berubah di awal kalimat, bukan setelah balasan rampung.
      const tag = bacaTagAwal(mentah)
      if (tag) store.expression = tag
    }
    const bisaUcap = mentah.slice(Math.max(pos, 0))
    const baru = bisaUcap.slice(diproses)
    if (!baru) return
    diproses = bisaUcap.length
    antrian.tambah(baru)
  }

  audioBusy.value = true
  try {
    await store.send(value, { onDelta: potongan => { mentah += potongan; proses() } })
    proses()
    antrian.tutup()
    await antrian.tungguSelesai()
  } finally { audioBusy.value = false; antrean = undefined }
}
async function toggleMic() {
  if (audioBusy.value) return
  if (!recording.value) { try { await recorder.start(); recording.value = true; audioStatus.value = 'Merekam...' } catch (e) { audioStatus.value = e instanceof Error ? e.message : String(e) }; return }
  recording.value = false; audioBusy.value = true; audioStatus.value = 'Mengenali suara...'
  try { input.value = await whisper.transcribe(await recorder.stop()); audioStatus.value = 'Transkripsi siap' }
  catch (e) { audioStatus.value = e instanceof Error ? e.message : String(e) }
  finally { audioBusy.value = false }
}
</script>

<template>
  <main class="shell">
    <section class="stage" aria-label="Panggung Silver Wolf">
      <header class="brand"><span class="sigil">SW</span><div><b>SILVER WOLF</b><small>STELLARON // LOCAL LINK</small></div></header>
      <canvas ref="canvas" :class="{ hidden: modelState === 'missing' }" />
      <div v-if="modelState === 'missing'" class="avatar-fallback" aria-label="Model Live2D belum dipasang">
        <div class="glitch" data-text="404">404</div><strong>MODEL OFFLINE</strong><span>Pasang aset Live2D di public/models/silverwolf</span>
      </div>
      <div class="expression"><span>RAUT</span><b>{{ store.expression }}</b></div>
      <div class="scanline" />
    </section>

    <section class="console">
      <header class="console-head">
        <div><span class="eyebrow">PRIVATE CHANNEL</span><h1>Catatan lapangan</h1></div>
        <button class="status" :class="{ online: store.ready }" @click="store.checkHealth" :title="store.healthError || store.health?.model">
          <i /> {{ store.ready ? 'TERHUBUNG' : 'PUTUS' }}
        </button>
      </header>
      <div v-if="store.health" class="telemetry"><span>{{ store.health.model }}</span><span>{{ store.health.memori }}</span></div>
      <div v-else-if="store.healthError" class="banner">Sidecar tidak menjawab — jalankan <code>npm run dev</code></div>

      <div ref="log" class="messages" aria-live="polite">
        <div v-if="!store.messages.length" class="empty"><span>01</span><h2>Link terenkripsi siap.</h2><p>Ketik pesan. Semua inferensi tetap berjalan di mesin lokal.</p></div>
        <article v-for="message in store.messages" :key="message.id" :class="['message', message.role, { error: message.error }]">
          <div class="meta">{{ message.role === 'user' ? 'MASTER' : 'SILVER WOLF' }} <time>#{{ String(message.id).padStart(3, '0') }}</time></div>
          <p>{{ message.content }}<i v-if="message.pending" class="cursor" /></p>
        </article>
      </div>

      <form class="composer" @submit.prevent="submit">
        <div class="compose-head">
          <label for="message">TRANSMISI BARU</label>
          <div class="audio-controls">
            <button type="button" class="tool" :class="{ active: recording }" :disabled="audioBusy" @click="toggleMic">{{ recording ? '■ STOP' : '● MIC' }}</button>
            <button type="button" class="tool" :class="{ active: voiceEnabled }" @click="voiceEnabled = !voiceEnabled">◖ SUARA</button>
          </div>
        </div>
        <div class="input-row"><textarea id="message" v-model="input" rows="2" maxlength="4000" placeholder="Tulis atau rekam suara..." :disabled="store.sending" @keydown.enter.exact.prevent="submit" /><button :disabled="!input.trim() || store.sending" aria-label="Kirim">↗</button></div>
        <small>{{ audioStatus || 'ENTER kirim · STT/TTS lokal' }} · {{ input.length }}/4000</small>
      </form>
    </section>
  </main>
</template>
