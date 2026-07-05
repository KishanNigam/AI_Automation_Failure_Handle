from __future__ import annotations

import logging
from typing import Any

import requests

from config import get_env

logger = logging.getLogger(__name__)


class OllamaClient:
    """Minimal client for the local Ollama HTTP API."""

    def __init__(self, base_url: str | None = None, model: str | None = None, timeout: int = 120) -> None:
        self.base_url = base_url or get_env("OLLAMA_BASE_URL", "http://localhost:11434/api/generate") or "http://localhost:11434/api/generate"
        self.model = model or get_env("OLLAMA_MODEL", "qwen3:8b") or "qwen3:8b"
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        """Send a prompt to Ollama and return only the final response text."""
        if not prompt:
            raise ValueError("Prompt cannot be empty")

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {"temperature": 0},
        }

        logger.info("Sending prompt to Ollama model %s", self.model)

        try:
            response = requests.post(self.base_url, json=payload, timeout=self.timeout)
            response.raise_for_status()
        except requests.Timeout as exc:
            logger.exception("Ollama request timed out")
            raise RuntimeError("Ollama request timed out") from exc
        except requests.RequestException as exc:
            logger.exception("Ollama request failed")
            raise RuntimeError("Unable to connect to Ollama") from exc

        try:
            data = response.json()
            result = data.get("response", "")
            return str(result).strip()
        except ValueError as exc:
            logger.exception("Ollama response was not valid JSON")
            raise RuntimeError("Invalid response from Ollama") from exc


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

    client = OllamaClient()
    result = client.generate("Reply with ONLY:\n\nOllama Connection Successful")
    print(result)
