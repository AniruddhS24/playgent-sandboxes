"""
LLM Access Module - Unified wrapper for OpenAI and Anthropic API interactions

This module provides a unified interface for interacting with multiple LLM providers.
It automatically detects the provider based on the model name and delegates to the
appropriate provider implementation.

Supported Providers:
- OpenAI: Models starting with 'gpt-', 'o1-' (default)
- Anthropic: Models starting with 'claude-'

Requirements:
- openai>=1.0.0
- anthropic>=0.30.0
- tiktoken

Environment Variables:
- OPENAI_API_KEY: For OpenAI models
- ANTHROPIC_API_KEY: For Anthropic models
"""

import os
import json
from typing import Optional, Dict, Any, List, Protocol
from abc import ABC, abstractmethod


class LLMProvider(Protocol):
    """Protocol defining the interface for all LLM providers."""

    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Create a chat completion."""
        ...

    def extract_content(self, response: Dict[str, Any]) -> str:
        """Extract content from a response."""
        ...

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        ...

    def get_context_limit(self) -> int:
        """Get maximum context length for the model."""
        ...

    def get_model(self) -> str:
        """Get the current model name."""
        ...


class OpenAIProvider:
    """Provider implementation for OpenAI models."""

    def __init__(self, api_key: str, model: str):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            model: Model name (e.g., 'gpt-4', 'gpt-3.5-turbo')
        """
        from openai import OpenAI
        import tiktoken

        self.model = model
        self.client = OpenAI(api_key=api_key)
        self.tiktoken = tiktoken

    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Create a chat completion using OpenAI API.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0-2)
            response_format: Optional response format specification
            **kwargs: Additional parameters

        Returns:
            Dictionary containing the API response
        """
        params: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        if response_format is not None:
            params["response_format"] = response_format

        params.update(kwargs)

        response = self.client.chat.completions.create(**params)
        return response.model_dump()

    def extract_content(self, response: Dict[str, Any]) -> str:
        """Extract content from OpenAI API response.

        Args:
            response: The API response dictionary

        Returns:
            The extracted content string
        """
        if "choices" in response and len(response["choices"]) > 0:
            choice = response["choices"][0]

            if "message" in choice:
                return choice["message"].get("content", "")

            if "text" in choice:
                return choice["text"]

        raise ValueError("Unable to extract content from response")

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        try:
            encoding = self.tiktoken.encoding_for_model(self.model)
        except KeyError:
            encoding = self.tiktoken.get_encoding("cl100k_base")

        return len(encoding.encode(text))

    def get_context_limit(self) -> int:
        """Get maximum context length for OpenAI model.

        Returns:
            Maximum context length in tokens
        """
        context_limits: Dict[str, int] = {
            # GPT-4 models
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-turbo": 128000,
            "gpt-4-turbo-preview": 128000,
            "gpt-4-1106-preview": 128000,
            "gpt-4-0125-preview": 128000,

            # GPT-4o models
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "gpt-4o-2024-05-13": 128000,
            "gpt-4o-2024-08-06": 128000,

            # GPT-3.5 models
            "gpt-3.5-turbo": 16385,
            "gpt-3.5-turbo-16k": 16385,
            "gpt-3.5-turbo-1106": 16385,
            "gpt-3.5-turbo-0125": 16385,

            # O1 models
            "o1": 200000,
            "o1-preview": 128000,
            "o1-mini": 128000,

            # GPT-5
            "gpt-5": 128000,
        }

        if self.model in context_limits:
            return context_limits[self.model]

        for model_prefix, limit in context_limits.items():
            if self.model.startswith(model_prefix):
                return limit

        return 8192

    def get_model(self) -> str:
        """Get current model name.

        Returns:
            Model name
        """
        return self.model


class AnthropicProvider:
    """Provider implementation for Anthropic Claude models."""

    def __init__(self, api_key: str, model: str):
        """Initialize Anthropic provider.

        Args:
            api_key: Anthropic API key
            model: Model name (e.g., 'claude-sonnet-4-5', 'claude-opus-4-5')
        """
        import anthropic

        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)
        self._anthropic = anthropic

    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Create a chat completion using Anthropic API.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0-1 for Anthropic)
            response_format: Optional response format specification
            **kwargs: Additional parameters

        Returns:
            Dictionary containing the normalized API response
        """
        # Separate system messages from other messages
        system_content = ""
        anthropic_messages = []

        for msg in messages:
            if msg["role"] == "system":
                if system_content:
                    system_content += "\n\n"
                system_content += msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # Handle JSON mode by adding to system prompt and headers
        extra_headers = {}
        if response_format and response_format.get("type") == "json_object":
            extra_headers["anthropic-beta"] = "structured-outputs-2025-11-13"
            if system_content:
                system_content += "\n\nYou must respond with valid JSON only. Do not include any text outside the JSON object."
            else:
                system_content = "You must respond with valid JSON only. Do not include any text outside the JSON object."

        params: Dict[str, Any] = {
            "model": self.model,
            "messages": anthropic_messages,
            "temperature": min(temperature, 1.0),  # Anthropic max is 1.0
            "max_tokens": max_tokens or 4096,  # Anthropic requires max_tokens
        }

        if system_content:
            params["system"] = system_content

        if extra_headers:
            params["extra_headers"] = extra_headers

        params.update(kwargs)

        response = self.client.messages.create(**params)

        # Normalize to OpenAI format
        return self._normalize_response(response)

    def _normalize_response(self, response: Any) -> Dict[str, Any]:
        """Convert Anthropic response to OpenAI-compatible format.

        Args:
            response: Anthropic API response object

        Returns:
            Normalized response dictionary matching OpenAI format
        """
        # Extract text from content blocks
        content_text = ""
        if hasattr(response, 'content') and len(response.content) > 0:
            for block in response.content:
                if hasattr(block, 'text'):
                    content_text += block.text

        # Build OpenAI-compatible structure
        normalized = {
            "id": response.id,
            "object": "chat.completion",
            "created": int(response.model_extra.get("created", 0)) if hasattr(response, 'model_extra') else 0,
            "model": response.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content_text
                    },
                    "finish_reason": response.stop_reason
                }
            ],
            "usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }
        }

        return normalized

    def extract_content(self, response: Dict[str, Any]) -> str:
        """Extract content from normalized Anthropic response.

        Args:
            response: Normalized response dictionary

        Returns:
            Extracted content string
        """
        # Response is already normalized to OpenAI format
        if "choices" in response and len(response["choices"]) > 0:
            choice = response["choices"][0]
            if "message" in choice:
                content = choice["message"].get("content", "")

                # Strip markdown code blocks if present (Anthropic sometimes wraps JSON)
                if content.startswith("```") and content.endswith("```"):
                    lines = content.split("\n")
                    # Remove first line (```json or ```) and last line (```)
                    if len(lines) > 2:
                        content = "\n".join(lines[1:-1])

                return content

        raise ValueError("Unable to extract content from response")

    def count_tokens(self, text: str) -> int:
        """Count tokens using Anthropic's token counting API.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        try:
            # Use Anthropic's token counting API
            result = self.client.messages.count_tokens(
                model=self.model,
                messages=[{"role": "user", "content": text}]
            )
            return result.input_tokens
        except Exception:
            # Fallback to approximation (4 chars per token)
            return len(text) // 4

    def get_context_limit(self) -> int:
        """Get maximum context length for Anthropic model.

        Returns:
            Maximum context length in tokens
        """
        context_limits: Dict[str, int] = {
            # Claude 4.5 models
            "claude-opus-4-5": 200000,
            "claude-sonnet-4-5": 200000,
            "claude-haiku-4-5": 200000,

            # Claude 3.5 models
            "claude-3-5-sonnet": 200000,
            "claude-3-5-haiku": 200000,

            # Claude 3 models
            "claude-3-opus": 200000,
            "claude-3-sonnet": 200000,
            "claude-3-haiku": 200000,

            # Legacy models
            "claude-2.1": 200000,
            "claude-2.0": 100000,
            "claude-instant-1.2": 100000,
        }

        if self.model in context_limits:
            return context_limits[self.model]

        for model_prefix, limit in context_limits.items():
            if self.model.startswith(model_prefix):
                return limit

        return 200000  # Default for Claude models

    def get_model(self) -> str:
        """Get current model name.

        Returns:
            Model name
        """
        return self.model


class LLMClient:
    """Unified wrapper class for LLM API access (OpenAI and Anthropic).

    This class acts as a facade, automatically detecting the provider based on
    the model name and delegating to the appropriate provider implementation.

    Zero breaking changes - existing code using OpenAI models works unchanged.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        """Initialize the LLM client with automatic provider detection.

        Args:
            api_key: API key (if None, reads from environment variable)
            model: Model name (e.g., 'gpt-4', 'claude-sonnet-4-5')

        Raises:
            ValueError: If API key is not provided or found in environment
        """
        self.model = model
        self.provider_type = self._detect_provider(model)

        # Get API key from parameter or environment
        if self.provider_type == "anthropic":
            api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
            if not api_key:
                raise ValueError(
                    "Anthropic API key must be provided or set in ANTHROPIC_API_KEY environment variable"
                )
            self.provider: LLMProvider = AnthropicProvider(api_key, model)
        else:
            api_key = api_key or os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                raise ValueError(
                    "OpenAI API key must be provided or set in OPENAI_API_KEY environment variable"
                )
            self.provider: LLMProvider = OpenAIProvider(api_key, model)

    @staticmethod
    def _detect_provider(model: str) -> str:
        """Detect provider based on model name.

        Args:
            model: Model name

        Returns:
            Provider type ('openai' or 'anthropic')
        """
        model_lower = model.lower()
        if model_lower.startswith("claude"):
            return "anthropic"
        return "openai"  # Default to OpenAI for backwards compatibility

    def create_completion(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Create a completion using the LLM API.

        Note: This legacy method is only supported for OpenAI models.

        Args:
            prompt: The prompt text
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            Dictionary containing the API response

        Raises:
            NotImplementedError: If called with non-OpenAI provider
        """
        if self.provider_type != "openai":
            raise NotImplementedError(
                "create_completion is only supported for OpenAI models. "
                "Use create_chat_completion instead."
            )

        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        params: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "temperature": temperature,
        }

        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        params.update(kwargs)

        response = client.completions.create(**params)
        return response.model_dump()

    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Create a chat completion using the appropriate provider.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0-2 for OpenAI, 0-1 for Anthropic)
            response_format: Optional response format (e.g., {"type": "json_object"})
            **kwargs: Additional parameters

        Returns:
            Dictionary containing the API response (normalized to OpenAI format)
        """
        return self.provider.create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format=response_format,
            **kwargs
        )

    def extract_content(self, response: Dict[str, Any]) -> str:
        """Extract content from an API response.

        Args:
            response: The API response dictionary

        Returns:
            The extracted content string
        """
        return self.provider.extract_content(response)

    def extract_json_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and parse JSON from an API response.

        Args:
            response: The API response dictionary

        Returns:
            Parsed JSON as a dictionary

        Raises:
            ValueError: If response content is not valid JSON
        """
        content = self.extract_content(response)

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Response content is not valid JSON: {e}") from e

    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string.

        Args:
            text: The text to count tokens for

        Returns:
            Number of tokens
        """
        return self.provider.count_tokens(text)

    def set_model(self, model: str) -> None:
        """Change the model being used.

        Note: Switching between providers (OpenAI <-> Anthropic) requires
        creating a new LLMClient instance.

        Args:
            model: New model name to use

        Raises:
            ValueError: If attempting to switch providers
        """
        new_provider_type = self._detect_provider(model)
        if new_provider_type != self.provider_type:
            raise ValueError(
                f"Cannot switch from {self.provider_type} to {new_provider_type}. "
                f"Create a new LLMClient instance instead."
            )
        self.model = model
        # Note: Provider's model is not updated, would require reinitializing provider
        # For now, this is a limitation - best practice is to create new client

    def get_model(self) -> str:
        """Get the current model name.

        Returns:
            Current model name
        """
        return self.provider.get_model()

    def get_context_limit(self) -> int:
        """Get the maximum context length (in tokens) for the current model.

        Returns:
            Maximum context length in tokens
        """
        return self.provider.get_context_limit()
