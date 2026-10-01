import { afterEach, describe, expect, it } from 'vitest'
import { request } from 'node:http'
import type { Server } from 'node:http'
import { CharacterAgent } from '@silverwolf/core-agent'
import { CharacterVault } from '@silverwolf/core-character'
import { bacaKonfig } from '@silverwolf/core-config'
import type { EnvSource } from '@silverwolf/core-config/coerce'
import { StubLlmProvider, createApiServer, listen, rapikanRiwayat } from '../src/index.ts'

const servers: Server[] = []
afterEach(() => Promise.all(servers.splice(0).map(s => new Promise<void>(r => s.close(() => r())))))
function call(port: number, path: string, method = 'GET', data?: unknown): Promise<{ status?: number; body: string; headers: Record<string, unknown> }> {
  return new Promise((resolve, reject) => { const body = data === undefined ? undefined : JSON.stringify(data); const req = request({ port, path, method, headers: body ? { 'content-type': 'application/json', 'content-length': Buffer.byteLength(body) } : {} }, res => { let text = ''; res.on('data', c => text += c); res.on('end', () => resolve({ status: res.statusCode, body: text, headers: res.headers })) }); req.on('error', reject); if (body) req.write(body); req.end() })
}
describe('server runtime', () => {
  it('merapikan dan membatasi riwayat', () => {
    expect(rapikanRiwayat([{ role: 'system', content: 'x' }, { role: 'assistant', content: 'jawab' }], 1, 3)).toEqual([{ role: 'assistant', content: 'jaw' }])
  })
  it('menyajikan health dan chat streaming stub', async () => {
    const source: EnvSource = { file: {}, environ: {}, warnings: [] }, config = bacaKonfig(source, '/tmp/test')
    const provider = new StubLlmProvider(), vault = new CharacterVault('/path/tidak-ada')
    const agent = new CharacterAgent({ provider, persona: 'persona' })
    const server = createApiServer({ config, provider, vault, agent, modelName: 'stub' }); servers.push(server)
    const port = await listen(server, 0, '127.0.0.1')
    const health = await call(port, '/api/health'); expect(JSON.parse(health.body)).toMatchObject({ ok: true, sisi: 'node' })
    const chat = await call(port, '/api/chat', 'POST', { messages: [{ role: 'user', content: 'hai' }] })
    expect(chat.status).toBe(200); expect(chat.body).toContain('[senyum]'); expect(chat.headers['x-model']).toBe('stub')
  })
})
