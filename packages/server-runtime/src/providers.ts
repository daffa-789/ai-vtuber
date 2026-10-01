import type { Availability, ChatMessage, GenerateOptions, LlmProvider } from '@silverwolf/provider-inference'

export interface OpenAiProviderOptions {
  id: 'llama-server' | 'ollama'
  baseUrl: string
  model: string
  fetch?: typeof globalThis.fetch
}

function pesanError(value: unknown): string {
  if (typeof value === 'object' && value && 'error' in value) {
    const error = (value as { error: unknown }).error
    if (typeof error === 'string') return error
    if (typeof error === 'object' && error && 'message' in error) return String((error as { message: unknown }).message)
  }
  return 'respons inferensi tidak valid'
}

async function* baris(response: Response): AsyncGenerator<string> {
  if (!response.body) return
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  try {
    while (true) {
      const { done, value } = await reader.read(); buffer += value ?? ''
      const lines = buffer.split(/\r?\n/); buffer = lines.pop() ?? ''
      for (const line of lines) if (line.trim()) yield line
      if (done) break
    }
    if (buffer.trim()) yield buffer
  } finally { reader.releaseLock() }
}

export class OpenAiCompatibleProvider implements LlmProvider {
  readonly id: 'llama-server' | 'ollama'
  private readonly baseUrl: string
  private readonly model: string
  private readonly doFetch: typeof globalThis.fetch
  constructor(options: OpenAiProviderOptions) {
    this.id = options.id; this.baseUrl = options.baseUrl.replace(/\/$/, ''); this.model = options.model
    this.doFetch = options.fetch ?? globalThis.fetch
  }
  async available(): Promise<Availability> {
    const path = this.id === 'ollama' ? '/api/tags' : '/health'
    try {
      const response = await this.doFetch(`${this.baseUrl}${path}`, { signal: AbortSignal.timeout(1500) })
      return { ok: response.ok, reason: response.ok ? 'siap' : `HTTP ${response.status}` }
    } catch (error) { return { ok: false, reason: error instanceof Error ? error.message : String(error) } }
  }
  async *stream(messages: ChatMessage[], options: GenerateOptions = {}): AsyncGenerator<string> {
    const controller = new AbortController()
    const timeout = options.deadline ? setTimeout(() => controller.abort(), Math.max(0, options.deadline - Date.now())) : undefined
    const onAbort = () => controller.abort()
    options.signal?.addEventListener('abort', onAbort, { once: true })
    try {
      const ollama = this.id === 'ollama'
      const response = await this.doFetch(`${this.baseUrl}${ollama ? '/api/chat' : '/v1/chat/completions'}`, {
        method: 'POST', headers: { 'content-type': 'application/json' }, signal: controller.signal,
        body: JSON.stringify(ollama
          ? { model: this.model, messages, stream: true, options: { temperature: options.temperature } }
          : { model: this.model, messages, stream: true, max_tokens: options.maxTokens, temperature: options.temperature }),
      })
      if (!response.ok) {
        let body: unknown; try { body = await response.json() } catch { body = await response.text() }
        throw new Error(`${this.id} HTTP ${response.status}: ${pesanError(body)}`)
      }
      for await (const line of baris(response)) {
        const payload = ollama ? line : line.replace(/^data:\s*/, '')
        if (payload === '[DONE]') break
        let data: unknown; try { data = JSON.parse(payload) } catch { continue }
        const chunk = ollama
          ? (data as { message?: { content?: string } }).message?.content
          : (data as { choices?: Array<{ delta?: { content?: string } }> }).choices?.[0]?.delta?.content
        if (chunk) yield chunk
      }
    } finally {
      if (timeout) clearTimeout(timeout)
      options.signal?.removeEventListener('abort', onAbort)
    }
  }
  async dispose(): Promise<void> {}
}

export class StubLlmProvider implements LlmProvider {
  readonly id = 'llama-server' as const
  async available() { return { ok: true, reason: 'stub' } }
  async *stream() { for (const p of ['[senyum] ', 'Sistem inti sudah hidup, ', 'Master.']) yield p }
  async dispose() {}
}
