import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { bersihkanTagAwal } from "@silverwolf/core-character/tags.js";
let nextId = 1;
const apiBase = typeof window === "undefined" ? "" : new URLSearchParams(window.location.search).get("api") ?? "";
const useCompanionStore = defineStore("companion", () => {
  const messages = ref([]);
  const health = ref();
  const healthError = ref("");
  const sending = ref(false);
  const expression = ref("netral");
  const ready = computed(() => Boolean(health.value?.ok));
  const loading = computed(() => Boolean(health.value?.loading));
  let timer = null;

  async function checkHealth() {
    try {
      const response = await fetch(`${apiBase}/api/health`, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      health.value = await response.json();
      healthError.value = "";
    } catch (error) {
      healthError.value = error instanceof Error ? error.message : String(error);
    }
  }

  function startPolling() {
    if (timer) return;
    const tick = async () => {
      await checkHealth();
      const jeda = health.value?.ok ? 8000 : 2000;
      timer = setTimeout(tick, jeda);
    };
    void tick();
  }

  function stopPolling() {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  }

  async function send(text, options = {}) {
    const clean = text.trim();
    if (!clean || sending.value) return "";
    messages.value.push({ id: nextId++, role: "user", content: clean });
    const reply = { id: nextId++, role: "assistant", content: "", pending: true };
    messages.value.push(reply);
    sending.value = true;
    try {
      const history = messages.value.filter((m) => !m.pending && !m.error).map(({ role, content }) => ({ role, content }));
      const response = await fetch(`${apiBase}/api/chat`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ messages: history }) });
      if (!response.ok) {
        const value = await response.json().catch(() => ({}));
        throw new Error(value.error ?? `HTTP ${response.status}`);
      }
      if (!response.body) throw new Error("browser tidak menyediakan response stream");
      const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        reply.content += value;
        options.onDelta?.(value);
      }
      const parsed = bersihkanTagAwal(reply.content);
      reply.content = parsed.teks;
      if (parsed.tag) expression.value = parsed.tag;
    } catch (error) {
      reply.error = true;
      reply.content = error instanceof Error ? error.message : String(error);
    } finally {
      reply.pending = false;
      sending.value = false;
    }
    return reply.error ? "" : reply.content;
  }
  return { messages, health, healthError, sending, expression, ready, loading, checkHealth, startPolling, stopPolling, send };
});
export {
  useCompanionStore
};
