import json
from typing import Any

import httpx


class OllamaError(Exception):
    """Raised when Ollama cannot satisfy a request."""


class OllamaClient:
    def __init__(self, base_url: str, model: str, timeout_seconds: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def get_installed_models(self) -> list[str]:
        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                response = client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise OllamaError("Ollama is unavailable or returned an invalid response") from exc

        models = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(models, list):
            raise OllamaError("Ollama returned an invalid model list")
        return [
            item.get("name")
            for item in models
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        ]

    def generate_json(
        self,
        *,
        system_prompt: str,
        context: dict[str, Any],
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                trust_env=False,
                follow_redirects=False,
            ) as client:
                response = client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "stream": False,
                        "format": schema,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {
                                "role": "user",
                                "content": json.dumps(context, ensure_ascii=False),
                            },
                        ],
                    },
                )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise OllamaError("Ollama failed to generate a briefing") from exc

        message = payload.get("message") if isinstance(payload, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise OllamaError("Ollama returned no briefing content")
        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama returned malformed briefing JSON") from exc
        if not isinstance(result, dict):
            raise OllamaError("Ollama briefing must be a JSON object")
        return result
