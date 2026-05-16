from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator

import httpx


@dataclass
class OllamaClient:
    base_url: str
    model: str
    timeout: float = 60.0

    async def generate(self, prompt: str, temperature: float = 0.2) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

    async def stream(self, prompt: str, temperature: float = 0.2) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": temperature},
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    data = httpx.Response(200, content=line).json()
                    chunk = data.get("response")
                    if chunk:
                        yield chunk

    async def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for text in texts:
                payload = {"model": self.model, "prompt": text}
                response = await client.post(f"{self.base_url}/api/embeddings", json=payload)
                response.raise_for_status()
                data = response.json()
                embeddings.append(data["embedding"])
                await asyncio.sleep(0)
        return embeddings
