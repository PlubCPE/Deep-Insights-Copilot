import os
import httpx
import logging
from typing import Optional, Any, Dict

logger = logging.getLogger("llm_client")
logging.basicConfig(level=logging.INFO)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "llama-3.3-8b")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # fallback OpenAI model

SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "You are a helpful assistant that answers based on provided context. Be concise and include provenance when available.")

async def _call_openrouter(prompt: str, max_tokens: int = 512, temperature: float = 0.0, timeout: float = 30.0) -> str:
    """
    Call OpenRouter chat completions endpoint. Returns the assistant text or raises an exception.
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set")

    url = "https://api.openrouter.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload, headers=headers)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            # include body for debugging without exposing secrets
            body = resp.text[:2000] if resp.text else ""
            logger.exception("OpenRouter HTTP error: %s", e)
            raise RuntimeError(f"OpenRouter HTTP error: {e} - body: {body}")

        data = resp.json()

    # parse response robustly
    try:
        # Common shape: choices[0].message.content (string)
        choices = data.get("choices") or []
        if choices:
            choice = choices[0]
            # try multiple possible content locations
            message = choice.get("message") or choice.get("delta") or {}
            if isinstance(message, dict):
                content = message.get("content") or message.get("text") or message.get("message") or None
                if isinstance(content, dict):
                    # sometimes content nested
                    content_text = content.get("content") or content.get("text") or None
                    if isinstance(content_text, str):
                        return content_text.strip()
                if isinstance(content, str):
                    return content.strip()
            # fallback to common 'text' or 'content' keys directly on choice
            if "text" in choice and isinstance(choice["text"], str):
                return choice["text"].strip()
            if "content" in choice and isinstance(choice["content"], str):
                return choice["content"].strip()
        # If no choices or couldn't parse, try a few other fields
        # Some providers put output in 'output' or at top-level 'generated_text'
        if isinstance(data.get("output"), str):
            return data.get("output").strip()
        if isinstance(data.get("generated_text"), str):
            return data.get("generated_text").strip()
    except Exception as e:
        logger.exception("Failed to parse OpenRouter response: %s", e)
        # fall through to returning the raw JSON string as a last resort
    return str(data)

async def _call_openai(prompt: str, max_tokens: int = 512, temperature: float = 0.0, timeout: float = 30.0) -> str:
    """
    Call OpenAI ChatCompletion API if OPENAI_API_KEY is present.
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")

    try:
        import openai
    except Exception as e:
        raise RuntimeError(f"OpenAI SDK not installed: {e}")

    openai.api_key = OPENAI_API_KEY

    # Use ChatCompletion API for compatibility
    try:
        resp = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        # parse response
        if resp and getattr(resp, "choices", None):
            msg = resp.choices[0].message
            if isinstance(msg, dict):
                return msg.get("content", "").strip()
            # some SDKs return objects with .content
            return str(resp.choices[0].message.content).strip()
        return str(resp)
    except Exception as e:
        logger.exception("OpenAI call failed: %s", e)
        raise RuntimeError(f"OpenAI error: {e}")

async def generate_completion(prompt: str, max_tokens: int = 512, temperature: float = 0.0, timeout: float = 30.0) -> str:
    """
    Main entrypoint used by the app. Tries OpenRouter first (if key present), then OpenAI,
    and falls back to a deterministic stub if neither is configured or calls fail.
    Returns the assistant text.
    """
    # Try OpenRouter
    if OPENROUTER_API_KEY:
        try:
            return await _call_openrouter(prompt, max_tokens=max_tokens, temperature=temperature, timeout=timeout)
        except Exception as e:
            logger.warning("OpenRouter call failed, falling back to OpenAI/stub: %s", e)

    # Try OpenAI
    if OPENAI_API_KEY:
        try:
            return await _call_openai(prompt, max_tokens=max_tokens, temperature=temperature, timeout=timeout)
        except Exception as e:
            logger.warning("OpenAI call failed, falling back to stub: %s", e)

    # Deterministic stub fallback
    stub = "STUB ANSWER: " + (prompt[:1000].replace("\n", " "))
    return stub
