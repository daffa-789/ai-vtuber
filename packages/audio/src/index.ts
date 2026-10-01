function wav(samples: Float32Array, sampleRate: number): Blob {
  const out = new ArrayBuffer(44 + samples.length * 2), view = new DataView(out)
  const ascii = (offset: number, text: string) => [...text].forEach((c, i) => view.setUint8(offset + i, c.charCodeAt(0)))
  ascii(0, 'RIFF'); view.setUint32(4, out.byteLength - 8, true); ascii(8, 'WAVE'); ascii(12, 'fmt ')
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true); view.setUint32(28, sampleRate * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true)
  ascii(36, 'data'); view.setUint32(40, samples.length * 2, true)
  samples.forEach((x, i) => view.setInt16(44 + i * 2, Math.max(-1, Math.min(1, x)) * (x < 0 ? 0x8000 : 0x7fff), true))
  return new Blob([out], { type: 'audio/wav' })
}

export class MicrophoneRecorder {
  private context?: AudioContext
  private stream?: MediaStream
  private processor?: ScriptProcessorNode
  private chunks: Float32Array[] = []
  async start(): Promise<void> {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } })
    this.context = new AudioContext({ sampleRate: 16_000 }); const source = this.context.createMediaStreamSource(this.stream)
    this.processor = this.context.createScriptProcessor(4096, 1, 1); this.chunks = []
    this.processor.onaudioprocess = event => this.chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)))
    source.connect(this.processor); this.processor.connect(this.context.destination)
  }
  async stop(): Promise<Blob> {
    if (!this.context) throw new Error('perekam belum berjalan')
    this.processor?.disconnect(); this.stream?.getTracks().forEach(track => track.stop())
    const sampleRate = this.context.sampleRate; await this.context.close()
    const length = this.chunks.reduce((n, x) => n + x.length, 0), joined = new Float32Array(length)
    let offset = 0; for (const chunk of this.chunks) { joined.set(chunk, offset); offset += chunk.length }
    this.context = undefined; return wav(joined, sampleRate)
  }
}
