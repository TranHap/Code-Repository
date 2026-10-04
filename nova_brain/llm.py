"""Couche d'accès au LLM. Fournisseur interchangeable : tout API compatible OpenAI
(Z.ai, Ollama local, Azure OpenAI...) en changeant base_url/modèle dans .env."""
import base64

from openai import OpenAI

from . import config

_client = None


def client() -> OpenAI:
    global _client
    if _client is None:
        if not config.LLM_API_KEY:
            raise RuntimeError("ZAI_API_KEY manquante dans .env")
        # Les modèles gratuits renvoient souvent 429 (surcharge) : le SDK réessaie avec backoff exponentiel.
        _client = OpenAI(api_key=config.LLM_API_KEY, base_url=config.LLM_BASE_URL, max_retries=6, timeout=120)
    return _client


def chat(messages, model=None, **kw):
    return client().chat.completions.create(model=model or config.TEXT_MODEL, messages=messages, **kw)


def vision(image_bytes: bytes, prompt: str, mime="image/png", model=None) -> str:
    b64 = base64.b64encode(image_bytes).decode()
    r = client().chat.completions.create(
        model=model or config.VISION_MODEL,
        messages=[{"role": "user", "content": [
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            {"type": "text", "text": prompt},
        ]}],
    )
    return r.choices[0].message.content.strip()
