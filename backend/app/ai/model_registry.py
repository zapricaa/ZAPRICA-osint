"""Configurable Model Registry for ZAPRICA AI Brain."""

from typing import Dict, Literal, Optional
from app.ai.model_config import model_config
from app.ai.providers.base import BaseLLMProvider
from app.ai.providers.google_gemini import GoogleGeminiProvider
from app.ai.providers.mock import MockLLMProvider
from app.core.config import settings

AgentRole = Literal["main_head", "browser_head", "terminal_head", "general"]


class ModelRegistry:
    """Manages model mappings and provider instances for different agent roles."""

    def __init__(self):
        self._role_model_overrides: Dict[AgentRole, str] = {}
        self._custom_providers: Dict[str, BaseLLMProvider] = {}
        self._active_provider: Optional[BaseLLMProvider] = None

    def get_model_for_role(self, role: AgentRole) -> str:
        """Resolve model name for a specific agent role without hardcoded model IDs."""
        if role in self._role_model_overrides:
            return self._role_model_overrides[role]

        if role == "main_head":
            return model_config.main_head_model
        elif role == "browser_head":
            return model_config.browser_head_model
        elif role == "terminal_head":
            return model_config.terminal_head_model
        else:
            return model_config.default_model

    def set_model_for_role(self, role: AgentRole, model_name: str) -> None:
        """Dynamically override model name for a specific agent role."""
        self._role_model_overrides[role] = model_name

    def register_provider(self, name: str, provider: BaseLLMProvider) -> None:
        """Register a custom LLM provider instance."""
        self._custom_providers[name] = provider

    def get_provider(self, provider_type: Optional[str] = None) -> BaseLLMProvider:
        """Get or create the appropriate LLM provider based on configuration."""
        # Check custom providers first
        if provider_type and provider_type in self._custom_providers:
            return self._custom_providers[provider_type]

        # Use explicitly requested provider type or fall back to system settings
        target_provider = provider_type or settings.LLM_PROVIDER

        if target_provider == "gemini":
            if not self._active_provider or not isinstance(self._active_provider, GoogleGeminiProvider):
                self._active_provider = GoogleGeminiProvider(
                    api_key=model_config.gemini_api_key,
                    default_model=model_config.default_model,
                    timeout_seconds=model_config.timeout_seconds,
                    max_retries=model_config.max_retries,
                )
            return self._active_provider

        # Default to hermetic mock provider for tests or local dev without API key
        if not self._active_provider or not isinstance(self._active_provider, MockLLMProvider):
            self._active_provider = MockLLMProvider()
        return self._active_provider

    def set_active_provider(self, provider: BaseLLMProvider) -> None:
        """Explicitly set the active provider (e.g. for testing)."""
        self._active_provider = provider


# Global model registry instance
registry = ModelRegistry()
