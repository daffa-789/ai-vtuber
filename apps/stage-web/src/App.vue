<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useCompanionStore } from '@silverwolf/stage-ui'
import { MicrophoneRecorder, WhisperTranscriber } from '@silverwolf/audio'
import { BrowserVoicePipeline } from '@silverwolf/pipelines-audio'

const store = useCompanionStore()
const input = ref(''), canvas = ref<HTMLCanvasElement>(), log = ref<HTMLElement>()
const modelState = ref<'loading' | 'ready' | 'missing'>('loading')
const recording = ref(false), audioBusy = ref(false), audioStatus = ref('')
const voiceEnabled = ref(true)
const recorder = new MicrophoneRecorder()
const whisper = new WhisperTranscriber({ language: 'indonesian', onProgress: p => { if (p.progress) audioStatus.value = `Whisper ${Math.round(p.progress)}%` } })
let voice: BrowserVoicePipeline | undefined
let playing: HTMLAudioElement | undefined
let renderer: import('@silverwolf/stage-ui-live2d').Live2DRenderer | undefined

onMounted(async () => {
  void store.checkHealth()
  if (!canvas.value) return
  try {
    const { Live2DRenderer } = await import('@silverwolf/stage-ui-live2d')
    renderer = new Live2DRenderer(canvas.value); await renderer.load('/models/silverwolf/silverwolf.model3.json'); modelState.value = 'ready'
  }
  catch (error) { console.warn('Live2D belum tersedia:', error); modelState.value = 'missing'; renderer?.destroy(); renderer = undefined }
})
onBeforeUnmount(() => { renderer?.destroy(); voice?.destroy(); playing?.pause() })
watch(() => store.expression, value => renderer?.setExpression(value))
watch(() => store.messages.map(m => `${m.id}:${m.content.length}`).join(','), async () => { await nextTick(); log.value?.scrollTo({ top: log.value.scrollHeight, behavior: 'smooth' }) })
async function speak(text: string) {
  if (!voiceEnabled.value || !text) return
  audioBusy.value = true; audioStatus.value = 'Menyusun suara...'
  try {
    voice ??= new BrowserVoicePipeline({ rvc: { contentVecUrl: '/assets/encoders/vec-768-layer-12.onnx', modelUrl: '/assets/voices/silverwolf/model.onnx', transpose: 10 } })
    const blob = await voice.synthesize(text), url = URL.createObjectURL(blob)
    playing = new Audio(url); playing.onended = () => URL.revokeObjectURL(url); await playing.play(); audioStatus.value = 'Suara aktif'
  } catch (error) { audioStatus.value = error instanceof Error ? error.message : String(error) }
  finally { audioBusy.value = false }
}
async function submit() { const value = input.value; input.value = ''; const reply = await store.send(value); await speak(reply) }
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
      <div v-else-if="store.healthError" class="banner">Sidecar tidak menjawab — jalankan <code>pnpm dev:server</code></div>

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
