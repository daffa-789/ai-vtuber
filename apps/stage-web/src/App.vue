<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useCompanionStore } from '@silverwolf/stage-ui'

const store = useCompanionStore()
const input = ref(''), canvas = ref<HTMLCanvasElement>(), log = ref<HTMLElement>()
const modelState = ref<'loading' | 'ready' | 'missing'>('loading')
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
onBeforeUnmount(() => renderer?.destroy())
watch(() => store.expression, value => renderer?.setExpression(value))
watch(() => store.messages.map(m => `${m.id}:${m.content.length}`).join(','), async () => { await nextTick(); log.value?.scrollTo({ top: log.value.scrollHeight, behavior: 'smooth' }) })
async function submit() { const value = input.value; input.value = ''; await store.send(value) }
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
        <label for="message">TRANSMISI BARU</label>
        <div><textarea id="message" v-model="input" rows="2" maxlength="4000" placeholder="Tulis sesuatu..." :disabled="store.sending" @keydown.enter.exact.prevent="submit" /><button :disabled="!input.trim() || store.sending" aria-label="Kirim">↗</button></div>
        <small>ENTER kirim · inferensi offline · {{ input.length }}/4000</small>
      </form>
    </section>
  </main>
</template>
