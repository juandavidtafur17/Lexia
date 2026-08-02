import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiClientError(Exception):
    pass


class GeminiClient:
    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise GeminiClientError("GEMINI_API_KEY is not configured")

        self.base_url = settings.GEMINI_API_URL.rstrip("/")
        self.model = settings.GEMINI_MODEL
        self.timeout = settings.GEMINI_TIMEOUT_SECONDS
        self.max_output_tokens = settings.GEMINI_MAX_OUTPUT_TOKENS
        self.temperature = 0.0
        self.client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self._default_headers(),
        )

    def _default_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.GEMINI_API_KEY}",
            "Content-Type": "application/json",
        }

    def summarize_review(self, review_text: str, metadata: dict[str, str] | None = None) -> str:
        payload = self._build_payload(review_text, metadata)
        response = self._post(payload)
        return self._extract_text(response.json())

    def _build_payload(self, review_text: str, metadata: dict[str, str] | None) -> dict[str, Any]:
        metadata_text = ""
        if metadata:
            metadata_text = "\n".join(f"- {key}: {value}" for key, value in metadata.items())

        prompt = (
            "Eres un analista de experiencia de cliente y producto para comercio electrónico empresarial. "
            "Recibe una reseña de un cliente y devuelve un resumen profesional, objetivo y accionable. "
            "El resultado debe incluir el sentimiento general, los puntos fuertes y las áreas de mejora.",
        )
        prompt = "".join([prompt[0], "\n\n"])
        prompt += f"Reseña:\n{review_text.strip()}\n\n"
        if metadata_text:
            prompt += f"Metadatos:\n{metadata_text}\n\n"
        prompt += (
            "Responde únicamente con un texto breve y con tono profesional. "
            "No incluyas numeración ni explicaciones adicionales."
        )

        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
            "prompt": prompt,
        }

    def _completion_path(self) -> str:
        if "openai" in self.base_url:
            return "/v1/completions"
        return "/v1/generate"

    def _post(self, payload: dict[str, Any]) -> httpx.Response:
        try:
            response = self.client.post(self._completion_path(), json=payload)
            response.raise_for_status()
            return response
        except httpx.RequestError as exc:
            logger.exception("Gemini request failed: %s", exc)
            raise GeminiClientError("Failed to reach Gemini API") from exc
        except httpx.HTTPStatusError as exc:
            logger.exception("Gemini returned non-success status: %s", exc.response.text)
            raise GeminiClientError("Gemini API request failed") from exc

    def _extract_text(self, data: dict[str, Any]) -> str:
        if output := data.get("output_text"):
            return str(output).strip()
        if choices := data.get("choices"):
            if isinstance(choices, list) and choices:
                first = choices[0]
                if isinstance(first, dict):
                    text = first.get("text") or first.get("message", {}).get("content")
                    if text:
                        return str(text).strip()
        if candidates := data.get("candidates"):
            if isinstance(candidates, list) and candidates:
                first = candidates[0]
                if isinstance(first, dict):
                    content = first.get("content")
                    if isinstance(content, list):
                        text = "".join(
                            item.get("text", "") if isinstance(item, dict) else str(item)
                            for item in content
                        )
                        if text:
                            return text.strip()
                    if isinstance(content, str):
                        return content.strip()
        if response := data.get("response"):
            if isinstance(response, dict):
                if output := response.get("output_text"):
                    return str(output).strip()
                if content := response.get("content"):
                    if isinstance(content, str):
                        return content.strip()
                    if isinstance(content, list):
                        return " ".join(str(item) for item in content).strip()
        raise GeminiClientError("Gemini API returned an unexpected response format")
