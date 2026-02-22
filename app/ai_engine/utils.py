"""
app/ai_engine/utils.py — Shared AI helper utilities.

Provides:
  - build_openrouter_llm()  : factory for the LangChain-compatible OpenRouter LLM
  - parse_json_safely()     : robust JSON extraction from messy LLM text
  - truncate_for_context()  : safely trim long strings to fit LLM context window
"""

import json
import logging
import re
from typing import Any

from langchain_openai import ChatOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# OpenRouter's base URL (drop-in OpenAI-compatible API)
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def build_openrouter_llm(temperature: float = 0.3) -> ChatOpenAI:
    """
    Build a LangChain ChatOpenAI client pointed at OpenRouter.

    Args:
        temperature: 0.0 = deterministic, 1.0 = creative.
                     Use low temp (0.1–0.3) for structured JSON outputs,
                     higher (0.6–0.8) for creative email drafting.

    Returns:
        A LangChain-compatible LLM instance.
    """
    return ChatOpenAI(
        model=settings.openrouter_model,
        api_key=settings.openrouter_api_key,
        base_url=OPENROUTER_BASE_URL,
        temperature=temperature,
        max_retries=3,
        # Pass required OpenRouter headers
        default_headers={
            "HTTP-Referer": "https://github.com/thasvithu/ai-lead-gen-agent",
            "X-Title": "AI Lead Gen Agent",
        },
    )


def parse_json_safely(text: str) -> dict[str, Any] | list[Any] | None:
    """
    Robustly extract and parse a JSON object or array from LLM output.

    Handles cases where the LLM wraps JSON in markdown code fences like:
        ```json
        { ... }
        ```

    Returns the parsed Python object, or None if parsing fails.
    """
    if not text:
        return None

    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    cleaned = re.sub(r"```(?:json)?\s*([\s\S]*?)```", r"\1", text.strip())
    cleaned = cleaned.strip()

    # Try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to extract the first JSON object {...} or array [...]
    for pattern in (r"\{[\s\S]*\}", r"\[[\s\S]*\]"):
        match = re.search(pattern, cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                continue

    logger.warning("Could not parse JSON from LLM output: %s", text[:200])
    return None


def truncate_for_context(text: str, max_chars: int = 2000) -> str:
    """
    Trim a string to max_chars to avoid exceeding LLM context window.
    Appends '...' if truncated.
    """
    if not text or len(text) <= max_chars:
        return text or ""
    return text[:max_chars] + "..."
