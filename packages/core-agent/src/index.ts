import type { ChatMessage, GenerateOptions, LlmProvider } from '@silverwolf/provider-inference'
import { CharacterVault, bacaTagAwal, gabungSystem, perbaruiMood, type Mood } from '@silverwolf/core-character'

export interface CharacterMemory {
  facts: string[]
  mood?: Mood
}
export interface AgentChat {
  readonly model: string
  readonly stream: AsyncGenerator<string>
}
export interface AgentOptions {
  provider: LlmProvider
  persona: string
  vault?: CharacterVault
  localPrompt?: boolean
  onError?: (error: unknown) => void
}

export class CharacterAgent {
  private readonly provider: LlmProvider
  private readonly persona: string
  private readonly vault?: CharacterVault
  private readonly localPrompt: boolean
  private readonly onError: (error: unknown) => void

  constructor(options: AgentOptions) {
    this.provider = options.provider
    this.persona = options.persona
    this.vault = options.vault
    this.localPrompt = options.localPrompt ?? true
    this.onError = options.onError ?? console.error
  }

  async memory(): Promise<CharacterMemory> {
    if (!this.vault?.available()) return { facts: [] }
    try { return { facts: await this.vault.bacaFakta(), mood: await this.vault.bacaMood() } }
    catch (error) { this.onError(error); return { facts: [] } }
  }

  async chat(history: ChatMessage[], options?: GenerateOptions): Promise<AgentChat> {
    const memory = await this.memory()
    const messages: ChatMessage[] = [
      { role: 'system', content: gabungSystem(this.persona, memory.facts, memory.mood, this.localPrompt) },
      ...history.filter(m => m.role !== 'system'),
    ]
    const source = this.provider.stream(messages, options)
    const self = this
    async function* alir(): AsyncGenerator<string> {
      let answer = ''
      let complete = false
      try {
        for await (const chunk of source) { answer += chunk; yield chunk }
        complete = true
      }
      finally {
        if (complete && answer) void self.persist(history, answer, memory).catch(self.onError)
      }
    }
    return { model: this.provider.id, stream: alir() }
  }

  private async persist(history: ChatMessage[], answer: string, memory: CharacterMemory): Promise<void> {
    if (!this.vault?.available()) return
    const mood = perbaruiMood(memory.mood, bacaTagAwal(answer))
    await this.vault.simpanMood(mood)
    const user = [...history].reverse().find(m => m.role === 'user')?.content ?? ''
    const ringkas = (s: string) => s.replace(/\s+/g, ' ').trim().slice(0, 240)
    await this.vault.catatHari(`Master: ${ringkas(user)} | Silver Wolf: ${ringkas(answer)}`)
  }

  dispose(): Promise<void> { return this.provider.dispose() }
}
