"""
Gemini API client module.
"""
import asyncio
import logging
from typing import AsyncGenerator

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class GeminiClient:
    """Async client for interacting with the Gemini API."""

    def __init__(self, api_key: str, model_name: str = 'gemini-2.0-flash'):
        """Initialize the Gemini client."""
        self.api_key = api_key
        self.model_name = model_name
        self.client = genai.Client(api_key=self.api_key)

    async def generate(self, prompt: str, system_instruction: str | None = None, temperature: float = 0.3, max_output_tokens: int = 1024) -> str:
        """Generate text from a prompt with retries and exponential backoff."""
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        if system_instruction:
            config.system_instruction = system_instruction
            
        retries = 3
        for attempt in range(retries):
            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config
                )
                return response.text
            except Exception as e:
                logger.error(f"Error generating content (attempt {attempt + 1}/{retries}): {e}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        return ""

    async def generate_stream(self, prompt: str, system_instruction: str | None = None, temperature: float = 0.3, max_output_tokens: int = 1024) -> AsyncGenerator[str, None]:
        """Generate text stream from a prompt with retries and exponential backoff."""
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        if system_instruction:
            config.system_instruction = system_instruction
            
        retries = 3
        for attempt in range(retries):
            try:
                response = await self.client.aio.models.generate_content_stream(
                    model=self.model_name,
                    contents=prompt,
                    config=config
                )
                async for chunk in response:
                    yield chunk.text
                return # If successful, exit retry loop
            except Exception as e:
                logger.error(f"Error generating content stream (attempt {attempt + 1}/{retries}): {e}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

    async def embed(self, texts: list[str], model: str = 'text-embedding-004') -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        retries = 3
        for attempt in range(retries):
            try:
                response = await self.client.aio.models.embed_content(
                    model=model,
                    contents=texts
                )
                return [embedding.values for embedding in response.embeddings]
            except Exception as e:
                logger.error(f"Error generating embeddings (attempt {attempt + 1}/{retries}): {e}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)
        return []

# Lazy singleton
_client_instance = None

def get_gemini_client(api_key: str, model_name: str = 'gemini-2.0-flash') -> GeminiClient:
    """Get or create the singleton GeminiClient instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = GeminiClient(api_key=api_key, model_name=model_name)
    return _client_instance
