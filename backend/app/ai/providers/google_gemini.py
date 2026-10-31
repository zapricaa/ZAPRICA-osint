"""Official Google Gen AI SDK (google-genai) provider for ZAPRICA."""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

try:
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError, ClientError, ServerError
except ImportError:
    genai = None  # type: ignore
    types = None  # type: ignore
    APIError = ClientError = ServerError = Exception  # type: ignore

from app.ai.model_config import model_config
from app.ai.providers.base import (
    BaseLLMProvider,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMValidationError,
)
from app.ai.schemas.reasoning import ProposedToolCall

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class GoogleGeminiProvider(BaseLLMProvider):
    """Google Gemini AI Brain implementation using official google-genai SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None,
    ):
        self.api_key = api_key if api_key is not None else model_config.gemini_api_key
        self.default_model = default_model or model_config.default_model
        self.timeout_seconds = timeout_seconds or model_config.timeout_seconds
        self.max_retries = max_retries or model_config.max_retries

        self._client: Optional[Any] = None
        if self.api_key and genai is not None:
            self._client = genai.Client(api_key=self.api_key)

    def _get_client(self) -> Any:
        if self._client is None:
            if not self.api_key:
                raise LLMProviderError(
                    "GEMINI_API_KEY is not configured. Set GEMINI_API_KEY environment variable."
                )
            if genai is None:
                raise LLMProviderError("google-genai package is not installed.")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def _execute_with_retry(self, coro_func, *args, **kwargs) -> Any:
        """Execute async coroutine with timeout and exponential backoff retry."""
        attempt = 0
        delay = model_config.retry_base_delay

        while attempt < self.max_retries:
            attempt += 1
            try:
                return await asyncio.wait_for(
                    coro_func(*args, **kwargs),
                    timeout=self.timeout_seconds,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Gemini API call timed out after %ds (attempt %d/%d)",
                    self.timeout_seconds,
                    attempt,
                    self.max_retries,
                )
                if attempt >= self.max_retries:
                    raise LLMTimeoutError(
                        f"Gemini API request timed out after {self.timeout_seconds}s across {self.max_retries} attempts"
                    )
            except ClientError as e:
                # HTTP 429 is resource exhausted / rate limit
                status_code = getattr(e, "code", None)
                msg = str(e).lower()
                if status_code == 429 or "429" in msg or "resource_exhausted" in msg:
                    logger.warning(
                        "Gemini rate limit encountered: %s. Backing off for %.1fs (attempt %d/%d)",
                        e,
                        delay,
                        attempt,
                        self.max_retries,
                    )
                    if attempt >= self.max_retries:
                        raise LLMRateLimitError(f"Gemini API rate limit exceeded: {e}")
                    await asyncio.sleep(delay)
                    delay *= 2.0
                else:
                    logger.error("Gemini ClientError: %s", e)
                    raise LLMProviderError(f"Gemini API client error: {e}") from e
            except ServerError as e:
                logger.warning(
                    "Gemini ServerError (%s). Retrying in %.1fs (attempt %d/%d)",
                    e,
                    delay,
                    attempt,
                    self.max_retries,
                )
                if attempt >= self.max_retries:
                    raise LLMProviderError(f"Gemini server error: {e}") from e
                await asyncio.sleep(delay)
                delay *= 2.0
            except APIError as e:
                logger.error("Gemini APIError: %s", e)
                raise LLMProviderError(f"Gemini API error: {e}") from e
            except Exception as e:
                logger.error("Unexpected error during Gemini execution: %s", e)
                raise LLMProviderError(f"Gemini execution failure: {e}") from e

        raise LLMProviderError(f"Gemini API call failed after {self.max_retries} retries")

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        """Generate plain text from Gemini."""
        client = self._get_client()
        target_model = model or self.default_model

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
        )

        async def _call():
            return await client.aio.models.generate_content(
                model=target_model,
                contents=prompt,
                config=config,
            )

        response = await self._execute_with_retry(_call)
        if not response or not response.text:
            raise LLMProviderError("Empty response received from Gemini model")
        return response.text

    async def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
    ) -> T:
        """Generate structured output strictly validated against response_schema."""
        client = self._get_client()
        target_model = model or self.default_model

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=response_schema,
        )

        async def _call():
            return await client.aio.models.generate_content(
                model=target_model,
                contents=prompt,
                config=config,
            )

        response = await self._execute_with_retry(_call)
        if not response or not response.text:
            raise LLMValidationError("Empty response received when expecting structured data")

        # If SDK provided parsed object
        if hasattr(response, "parsed") and response.parsed is not None:
            if isinstance(response.parsed, response_schema):
                return response.parsed

        # Fallback to direct Pydantic JSON validation
        try:
            return response_schema.model_validate_json(response.text)
        except ValidationError as val_err:
            logger.error("Failed to parse Gemini output into schema %s: %s", response_schema.__name__, val_err)
            raise LLMValidationError(
                f"Model output violated schema {response_schema.__name__}: {val_err}"
            ) from val_err

    async def propose_tool_call(
        self,
        prompt: str,
        available_tools: List[Dict[str, Any]],
        system_instruction: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[ProposedToolCall]:
        """Propose a tool call from available tools list."""
        tools_summary = "\n".join(
            f"- Tool '{t.get('name')}': {t.get('description', 'No description')} (Inputs: {t.get('parameters_schema')})"
            for t in available_tools
        )
        tool_prompt = (
            f"{prompt}\n\n"
            f"AVAILABLE TOOLS:\n{tools_summary}\n\n"
            f"Select the single most appropriate tool from the available list and specify valid arguments. "
            f"If no tool is appropriate or needed, justify why."
        )

        return await self.generate_structured(
            prompt=tool_prompt,
            response_schema=ProposedToolCall,
            system_instruction=system_instruction,
            model=model,
            temperature=0.1,
        )

    async def is_available(self) -> bool:
        """Verify API key is set and SDK is loaded."""
        if not self.api_key or genai is None:
            return False
        return True
