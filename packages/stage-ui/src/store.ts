import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { bersihkanTagAwal } from '@silverwolf/core-character/tags.ts'
import type { EmotionTag } from '@silverwolf/core-character/mood.ts'

export interface UiMessage { id: number; role: 'user' | 'assistant'; content: string; pending?: boolean; error?: boolean }
export interface SidecarHealth { ok: boolean; model: string; memori: string; stt?: { siap: boolean; alasan: string } }
let nextId = 1

export const useCompanionStore = defineStore('companion', () => {
  const messages = ref<UiMessage[]>([])
  const health = ref<SidecarHealth>()
  const healthError = ref('')
  const sending = ref(false)
  const expression = ref<EmotionTag>('netral')
  const ready = computed(() => Boolean(health.value?.ok))

  async function checkHealth(): Promise<void> {
    try {
      const response = await fetch('/api/health', { cache: 'no-store' })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      health.value = await response.json() as SidecarHealth; healthError.value = ''
    } catch (error) { healthError.value = error instanceof Error ? error.message : String(error) }
  }

  async function send(text: string): Promise<string> {
    const clean = text.trim(); if (!clean || sending.value) return ''
    messages.value.push({ id: nextId++, role: 'user', content: clean })
    const reply: UiMessage = { id: nextId++, role: 'assistant', content: '', pending: true }
    messages.value.push(reply); sending.value = true
    try {
      const history = messages.value.filter(m => !m.pending && !m.error).map(({ role, content }) => ({ role, content }))
      const response = await fetch('/api/chat', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ messages: history }) })
      if (!response.ok) { const value = await response.json().catch(() => ({})) as { error?: string }; throw new Error(value.error ?? `HTTP ${response.status}`) }
      if (!response.body) throw new Error('browser tidak menyediakan response stream')
      const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
      while (true) { const { done, value } = await reader.read(); if (done) break; reply.content += value }
      const parsed = bersihkanTagAwal(reply.content); reply.content = parsed.teks; if (parsed.tag) expression.value = parsed.tag
    } catch (error) { reply.error = true; reply.content = error instanceof Error ? error.message : String(error) }
    finally { reply.pending = false; sending.value = false }
    return reply.error ? '' : reply.content
  }

  return { messages, health, healthError, sending, expression, ready, checkHealth, send }
})
