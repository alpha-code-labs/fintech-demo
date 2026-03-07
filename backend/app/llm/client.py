"""
LLM client — Gemini Flash via REST API.

Uses GEMINI_API_KEY env var. Returns None when no key is set,
so callers can fall back gracefully.
"""
import json
import logging
import os

import requests

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.0-flash"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
)
TIMEOUT = 30  # seconds


def generate(prompt: str, max_tokens: int = 512) -> str | None:
    """
    Send a prompt to Gemini and return the text response.
    Returns None if no API key is configured or if the call fails.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.debug("GEMINI_API_KEY not set — skipping LLM call")
        return None

    try:
        resp = requests.post(
            GEMINI_URL,
            params={"key": api_key},
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": 0.3,
                },
            },
            timeout=TIMEOUT,
        )

        if resp.status_code != 200:
            logger.warning(f"Gemini API error {resp.status_code}: {resp.text[:200]}")
            return None

        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            return None

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            return None

        return parts[0].get("text", "").strip()

    except Exception as e:
        logger.warning(f"Gemini call failed: {e}")
        return None
