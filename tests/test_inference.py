"""Unit test untuk inferensi LLM."""

from huohuo.inference.llama_client import LlamaClient


def test_llama_client_generate_fallback():
    client = LlamaClient()
    # Panggil dengan prompt sapaan
    messages = [{"role": "user", "content": "Halo sayang!"}]
    emotion, text = client.generate(messages)

    assert emotion in ("senyum", "goda", "kaget", "netral", "sebal")
    assert "HuoHuo" in text or "Master" in text or "pacar" in text
    assert len(text) > 10


def test_llama_client_cemburu_fallback():
    client = LlamaClient()
    # Panggil dengan karakter HSR lain untuk menguji logika cemburu
    messages = [{"role": "user", "content": "Aku lagi ngobrol sama Kafka."}]
    emotion, text = client.generate(messages)

    assert emotion == "sebal"
    assert "cemburu" in text.lower() or "pacarmu" in text.lower()


def test_llama_client_health_check_offline():
    # Menguji pemanggilan endpoint offline tidak menghasilkan crash
    client = LlamaClient()
    healthy = client.is_healthy(timeout_detik=0.5)
    assert isinstance(healthy, bool)
