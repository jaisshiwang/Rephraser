from __future__ import annotations

import json
import os
from typing import Any, Dict, Protocol


class JsonLLM(Protocol):
    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        ...


class OpenAIJsonLLM:
    def __init__(self, model: str = "") -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("OpenAI support requires the 'openai' package") from exc

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = OpenAI()
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        response = self.client.responses.create(
            model=self.model,
            instructions=system_prompt,
            input=user_prompt,
        )
        return parse_json_object(response.output_text)


def parse_json_object(value: str) -> Dict[str, Any]:
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        raise ValueError("LLM response must be a JSON object")
    return parsed


def default_llm() -> JsonLLM:
    return OpenAIJsonLLM()

