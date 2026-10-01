import { createServer, type IncomingMessage, type Server, type ServerResponse } from 'node:http'
import type { AddressInfo } from 'node:net'
import type { ChatMessage, LlmProvider } from '@silverwolf/provider-inference'
import type { Konfig } from '@silverwolf/core-config'
import type { CharacterAgent } from '@silverwolf/core-agent'
import type { CharacterVault } from '@silverwolf/core-character'
import type { HealthResponse } from '@silverwolf/server-shared'

export interface HttpRuntime { config: Konfig; agent: CharacterAgent; provider: LlmProvider; vault: CharacterVault; modelName: string }
const cors = { 'access-control-allow-origin': '*', 'access-control-allow-headers': 'content-type', 'access-control-allow-methods': 'GET, POST, OPTIONS' }
function json(res: ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { ...cors, 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }); res.end(JSON.stringify(body))
}
async function body(req: IncomingMessage, max: number): Promise<Buffer> {
  const declared = Number(req.headers['content-length'] ?? 0); if (declared > max) throw new RangeError('body terlalu besar')
  const chunks: Buffer[] = []; let size = 0
  for await (const chunk of req) { const data = Buffer.from(chunk); size += data.length; if (size > max) throw new RangeError('body terlalu besar'); chunks.push(data) }
  return Buffer.concat(chunks)
}
export function rapikanRiwayat(raw: unknown, maxMessages: number, maxChars: number): ChatMessage[] {
  if (!Array.isArray(raw)) return []
  const hasil: ChatMessage[] = []
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue
    const record = item as Record<string, unknown>
    let content = typeof record.content === 'string' ? record.content : ''
    if (!content && Array.isArray(record.parts)) content = record.parts.map(p => typeof p === 'object' && p && 'text' in p ? String((p as { text: unknown }).text) : '').join(' ')
    if (!content.trim()) continue
    hasil.push({ role: record.role === 'assistant' || record.role === 'model' ? 'assistant' : 'user', content: content.slice(0, maxChars) })
  }
  return hasil.slice(-maxMessages)
}

export function createApiServer(runtime: HttpRuntime): Server {
  return createServer(async (req, res) => {
    try {
      const url = new URL(req.url ?? '/', 'http://localhost')
      if (req.method === 'OPTIONS') { res.writeHead(204, cors); res.end(); return }
      if (url.pathname === '/api/health' && req.method === 'GET') {
        const llm = await runtime.provider.available()
        const health: HealthResponse = {
          ok: true, model: `${runtime.modelName}${llm.ok ? '' : `/tidak-jalan (${llm.reason})`}`, cadangan: [], key: true,
          tts: 'belum tersedia (Fase 3)', stt: { hidup: runtime.config.sttHidup, model: runtime.config.sttModel, siap: false, alasan: 'belum tersedia (Fase 2)' },
          memori: runtime.vault.available() ? 'memori lokal (silver_wolf_memory/)' : runtime.vault.unavailableReason(), sisi: 'node',
        }
        json(res, 200, health); return
      }
      if (url.pathname === '/api/chat' && req.method === 'GET') { json(res, 405, { error: 'gunakan POST untuk /api/chat' }); return }
      if (url.pathname === '/api/chat' && req.method === 'POST') {
        let parsed: unknown
        try { parsed = JSON.parse((await body(req, runtime.config.maksBody)).toString('utf8')) } catch (error) {
          if (error instanceof RangeError) { json(res, 413, { error: error.message }); return }
          json(res, 400, { error: 'body harus JSON: { messages: [{role, content}] }' }); return
        }
        const messages = rapikanRiwayat((parsed as { messages?: unknown })?.messages, runtime.config.maksPesan, runtime.config.maksKarakter)
        if (!messages.length) { json(res, 400, { error: 'riwayat kosong' }); return }
        const chat = await runtime.agent.chat(messages, { maxTokens: 512, temperature: 0.7 })
        // Pacu token pertama sebelum 200 agar kegagalan boot masih dapat menjadi 503.
        const first = await chat.stream.next()
        res.writeHead(200, { ...cors, 'content-type': 'text/plain; charset=utf-8', 'cache-control': 'no-store', 'x-accel-buffering': 'no', 'x-model': runtime.modelName })
        if (!first.done) res.write(first.value)
        for await (const chunk of chat.stream) { if (!res.write(chunk)) await new Promise<void>(resolve => res.once('drain', resolve)) }
        res.end(); return
      }
      json(res, 404, { error: 'tidak ditemukan' })
    } catch (error) {
      if (!res.headersSent) json(res, 503, { error: error instanceof Error ? error.message : String(error) })
      else res.destroy(error instanceof Error ? error : undefined)
    }
  })
}

export async function listen(server: Server, port: number, host = '0.0.0.0'): Promise<number> {
  await new Promise<void>((resolve, reject) => { server.once('error', reject); server.listen(port, host, resolve) })
  return (server.address() as AddressInfo).port
}
