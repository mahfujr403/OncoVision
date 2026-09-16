"""
Gemini API client module.
"""
import asyncio
import logging
import re
from typing import AsyncGenerator

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

DEFAULT_LLM_MODEL = "gemini-3.6-flash"
FALLBACK_LLM_MODELS = [
    "gemini-3.6-flash",
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
]
DEFAULT_EMBEDDING_MODEL = "text-embedding-004"
FALLBACK_EMBEDDING_MODELS = ["text-embedding-004", "embedding-001"]

_DEPRECATED_MODELS = {"gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.5-flash"}


class GeminiClient:
    """Async client for interacting with the Gemini API."""

    def __init__(self, api_key: str, model_name: str = DEFAULT_LLM_MODEL):
        """Initialize the Gemini client."""
        self.api_key = api_key
        # Automatically upgrade deprecated model requests
        if model_name in _DEPRECATED_MODELS:
            self.model_name = DEFAULT_LLM_MODEL
        else:
            self.model_name = model_name or DEFAULT_LLM_MODEL
        self.client = genai.Client(api_key=self.api_key)

    def _get_generation_models(self) -> list[str]:
        """Return priority list of models to try for generation."""
        models = [self.model_name]
        for m in FALLBACK_LLM_MODELS:
            if m not in models:
                models.append(m)
        return models

    def _get_embedding_models(self, requested_model: str) -> list[str]:
        """Return priority list of models to try for embedding."""
        models = [requested_model]
        for m in FALLBACK_EMBEDDING_MODELS:
            if m not in models:
                models.append(m)
        return models

    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int = 1024,
    ) -> str:
        """Generate text from a prompt with retries, model fallback, and exponential backoff."""
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        if system_instruction:
            config.system_instruction = system_instruction

        models_to_try = self._get_generation_models()
        last_exception = None

        for model in models_to_try:
            retries = 2
            for attempt in range(retries):
                try:
                    response = await self.client.aio.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=config,
                    )
                    # If fallback worked, remember it
                    if model != self.model_name:
                        logger.info("Successfully used fallback model: %s", model)
                        self.model_name = model
                    return response.text or ""
                except Exception as e:
                    last_exception = e
                    err_str = str(e)
                    is_model_unavail = "not found" in err_str.lower() or "not available" in err_str.lower() or "404" in err_str
                    logger.warning(
                        "Error generating content with %s (attempt %d/%d): %s",
                        model,
                        attempt + 1,
                        retries,
                        e,
                    )
                    if is_model_unavail:
                        # Extract any recommended model from Google's error message
                        if "use" in err_str:
                            rec_match = re.search(r"models/(gemini-[\w\.-]+)", err_str.split("use")[-1])
                            if rec_match:
                                rec_model = rec_match.group(1)
                                if rec_model not in models_to_try:
                                    logger.info("Found recommended model in API error: %s", rec_model)
                                    models_to_try.append(rec_model)
                        # Break retry loop immediately and try next model
                        break
                    if attempt < retries - 1:
                        await asyncio.sleep(2 ** attempt)

        if last_exception:
            raise last_exception
        return ""

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """Generate text stream from a prompt with retries and exponential backoff."""
        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        if system_instruction:
            config.system_instruction = system_instruction

        models_to_try = self._get_generation_models()
        last_exception = None

        for model in models_to_try:
            retries = 2
            for attempt in range(retries):
                try:
                    response = await self.client.aio.models.generate_content_stream(
                        model=model,
                        contents=prompt,
                        config=config,
                    )
                    async for chunk in response:
                        yield chunk.text
                    if model != self.model_name:
                        self.model_name = model
                    return
                except Exception as e:
                    last_exception = e
                    err_str = str(e)
                    is_model_unavail = "not found" in err_str.lower() or "not available" in err_str.lower() or "404" in err_str
                    logger.warning(
                        "Error generating content stream with %s (attempt %d/%d): %s",
                        model,
                        attempt + 1,
                        retries,
                        e,
                    )
                    if is_model_unavail:
                        break
                    if attempt < retries - 1:
                        await asyncio.sleep(2 ** attempt)

        if last_exception:
            raise last_exception

    async def embed(
        self, texts: list[str], model: str = DEFAULT_EMBEDDING_MODEL
    ) -> list[list[float]]:
        """Generate embeddings for a list of texts with model fallback."""
        models_to_try = self._get_embedding_models(model)
        last_exception = None

        for emb_model in models_to_try:
            retries = 2
            for attempt in range(retries):
                try:
                    response = await self.client.aio.models.embed_content(
                        model=emb_model,
                        contents=texts,
                    )
                    return [embedding.values for embedding in response.embeddings]
                except Exception as e:
                    last_exception = e
                    err_str = str(e)
                    is_model_unavail = "not found" in err_str.lower() or "not available" in err_str.lower() or "404" in err_str
                    logger.warning(
                        "Error generating embeddings with %s (attempt %d/%d): %s",
                        emb_model,
                        attempt + 1,
                        retries,
                        e,
                    )
                    if is_model_unavail:
                        break
                    if attempt < retries - 1:
                        await asyncio.sleep(2 ** attempt)

        if last_exception:
            raise last_exception
        return []


# Lazy singleton
_client_instance = None


def get_gemini_client(
    api_key: str, model_name: str = DEFAULT_LLM_MODEL
) -> GeminiClient:
    """Get or create the singleton GeminiClient instance."""
    global _client_instance
    target_model = DEFAULT_LLM_MODEL if model_name in _DEPRECATED_MODELS else (model_name or DEFAULT_LLM_MODEL)
    if _client_instance is None or _client_instance.model_name in _DEPRECATED_MODELS:
        _client_instance = GeminiClient(api_key=api_key, model_name=target_model)
    return _client_instance
