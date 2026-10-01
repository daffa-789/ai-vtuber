import { describe, expect, it } from 'vitest'
import type { ChatMessage, LlmProvider } from '@silverwolf/provider-inference'
import { CharacterAgent } from '../src/index.ts'

class Fake implements LlmProvider {
  readonly id = 'llama-server' as const
  seen: ChatMessage[] = []
  async available() { return { ok: true, reason: 'siap' } }
  async *stream(messages: ChatMessage[]) { this.seen = messages; yield '[senyum] '; yield 'halo' }
  async dispose() {}
}

describe('CharacterAgent', () => {
  it('menambahkan system prompt dan mempertahankan streaming', async () => {
    const provider = new Fake()
    const agent = new CharacterAgent({ provider, persona: 'Kamu Silver Wolf.' })
    const result = await agent.chat([{ role: 'user', content: 'Hai' }])
    let text = ''; for await (const part of result.stream) text += part
    expect(text).toBe('[senyum] halo')
    expect(provider.seen[0]).toMatchObject({ role: 'system' })
    expect(provider.seen[1]).toEqual({ role: 'user', content: 'Hai' })
  })
})
