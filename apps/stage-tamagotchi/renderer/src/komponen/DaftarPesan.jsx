import { defineComponent, nextTick, ref, watch } from "vue";
const DaftarPesan = defineComponent({
  name: "DaftarPesan",
  props: { pesan: { type: Array, required: true } },
  setup(props) {
    const wadah = ref();
    watch(
      () => props.pesan.map((m) => `${m.id}:${m.content.length}:${m.pending}`).join("|"),
      async () => {
        await nextTick();
        wadah.value?.scrollTo({ top: wadah.value.scrollHeight, behavior: "smooth" });
      },
      { deep: true }
    );
    return () => <div ref={wadah} class="messages" aria-live="polite">
        {!props.pesan.length && <div class="empty">
            <div class="empty-badge">⚡ STELLARON LINK // ENCRYPTED SESSION</div>
            <h2>Halo Master, ada misi apa hari ini?</h2>
            <p>Ketik pesan ke terminal. Seluruh inferensi AI berjalan 100% offline dan lokal di sistem ini.</p>
          </div>}
        {props.pesan.map((message) => <article key={message.id} class={["message", message.role, { error: message.error }]}>
            <div class="meta">
              <span>{message.role === "user" ? "👤 MASTER" : "👾 SILVER WOLF"}</span>
              <time>#{String(message.id).padStart(3, "0")}</time>
            </div>
            <div class="bubble">
              {message.error && <div class="error-tag">⚠ TRANSMISSION ERROR</div>}
              {message.pending && !message.content ? (
                <div class="typing-loader">
                  <span class="typing-dot" />
                  <span class="typing-dot" />
                  <span class="typing-dot" />
                  <span class="typing-text">MENERIMA TRANSMISI NEURAL...</span>
                </div>
              ) : (
                <p>
                  {message.content}
                  {message.pending && <span class="typing-cursor">▌</span>}
                </p>
              )}
            </div>
          </article>)}
      </div>;
  }
});
export {
  DaftarPesan
};
