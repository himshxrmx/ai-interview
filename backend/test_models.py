"""
Ad-hoc probe: check which OpenRouter model IDs the current key can actually reach.

Usage: python test_models.py
"""

import asyncio
import os
import sys

import httpx
from dotenv import load_dotenv

from llm_service import MODEL, FALLBACK_MODELS

load_dotenv()


async def test():
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        print("OPENROUTER_API_KEY is not set — add it to .env first.")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {key}"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        for model in [MODEL] + FALLBACK_MODELS:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 10,
                },
            )
            print(f"{model}: {response.status_code} {response.text[:160]}")


asyncio.run(test())
