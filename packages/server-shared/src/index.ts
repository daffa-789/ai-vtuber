import type { ChatMessage } from '@silverwolf/provider-inference'
export interface ChatRequest { messages: ChatMessage[] }
export interface TtsRequest { text: string }
export interface ApiError { error: string }
export interface HealthResponse {
  ok: boolean
  model: string
  cadangan: string[]
  key: boolean
  tts: string
  stt: { hidup: boolean; model: string; siap: boolean; alasan: string }
  memori: string
  sisi: 'node'
}
