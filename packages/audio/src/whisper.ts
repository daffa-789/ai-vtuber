export interface WhisperProgress { status: string; progress?: number; file?: string }
export interface WhisperOptions { model?: string; language?: string; onProgress?: (progress: WhisperProgress) => void }

type AsrPipeline = (audio: Float32Array, options: Record<string, unknown>) => Promise<{ text: string } | Array<{ text: string }>>

export class WhisperTranscriber {
  private task?: Promise<AsrPipeline>
  constructor(private readonly options: WhisperOptions = {}) {}
  async load(): Promise<void> { await this.pipeline() }
  private async pipeline(): Promise<AsrPipeline> {
    this.task ??= (async () => {
      const transformers = await import('@huggingface/transformers')
      transformers.env.allowLocalModels = true
      transformers.env.allowRemoteModels = true
      return await transformers.pipeline(
        'automatic-speech-recognition',
        this.options.model ?? 'onnx-community/whisper-base',
        { dtype: 'q8', progress_callback: this.options.onProgress },
      ) as unknown as AsrPipeline
    })()
    return this.task
  }
  async transcribe(wav: Blob): Promise<string> {
    const context = new AudioContext({ sampleRate: 16_000 })
    try {
      const decoded = await context.decodeAudioData(await wav.arrayBuffer())
      const input = decoded.getChannelData(0)
      const result = await (await this.pipeline())(input, {
        language: this.options.language ?? 'indonesian',
        task: 'transcribe', chunk_length_s: 30, stride_length_s: 5,
      })
      return (Array.isArray(result) ? result.map(x => x.text).join(' ') : result.text).trim()
    } finally { await context.close() }
  }
}
