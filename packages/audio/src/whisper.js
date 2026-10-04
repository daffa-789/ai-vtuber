class WhisperTranscriber {
  constructor(options = {}) {
    this.options = options;
  }
  task;
  async load() {
    await this.pipeline();
  }
  async pipeline() {
    this.task ??= (async () => {
      const transformers = await import("@huggingface/transformers");
      transformers.env.allowLocalModels = true;
      transformers.env.allowRemoteModels = true;
      return await transformers.pipeline(
        "automatic-speech-recognition",
        this.options.model ?? "onnx-community/whisper-base",
        { dtype: "q8", progress_callback: this.options.onProgress }
      );
    })();
    return this.task;
  }
  async transcribe(wav) {
    const context = new AudioContext({ sampleRate: 16e3 });
    try {
      const decoded = await context.decodeAudioData(await wav.arrayBuffer());
      const input = decoded.getChannelData(0);
      const result = await (await this.pipeline())(input, {
        language: this.options.language ?? "indonesian",
        task: "transcribe",
        chunk_length_s: 30,
        stride_length_s: 5
      });
      return (Array.isArray(result) ? result.map((x) => x.text).join(" ") : result.text).trim();
    } finally {
      await context.close();
    }
  }
}
export {
  WhisperTranscriber
};
