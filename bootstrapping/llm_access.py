"""
LLM Access Module - Wrapper for OpenAI API interactions
"""

import os
import json
from typing import Optional, Dict, Any, List
from openai import OpenAI
import tiktoken


class LLMClient:
    """Wrapper class for OpenAI API access."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4"):
        """Initialize the LLM client.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model name to use (default: gpt-4)
        """
        self.api_key: str = api_key or os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            raise ValueError("OpenAI API key must be provided or set in OPENAI_API_KEY environment variable")

        self.model: str = model
        self.client: OpenAI = OpenAI(api_key=self.api_key)

    def create_completion(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Create a completion using the OpenAI API.

        Args:
            prompt: The prompt text to send to the model
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0-2)
            **kwargs: Additional parameters to pass to the API

        Returns:
            Dictionary containing the API response
        """
        params: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "temperature": temperature,
        }

        if max_tokens is not None:
            params["max_tokens"] = max_tokens

        params.update(kwargs)

        response = self.client.completions.create(**params)
        return response.model_dump()

    def create_chat_completion(
        self,
        messages: List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: float = 1.0,
        response_format: Optional[Dict[str, Any]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Create a chat completion using the OpenAI API.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature (0-2)
            response_format: Optional response format specification (e.g., {"type": "json_object"})
            **kwargs: Additional parameters to pass to the API

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
        """Extract content from an API response.

        Args:
            response: The API response dictionary

        Returns:
            The extracted content string
        """
        # Handle chat completion response
        if "choices" in response and len(response["choices"]) > 0:
            choice = response["choices"][0]

            # Chat completion format
            if "message" in choice:
                return choice["message"].get("content", "")

            # Legacy completion format
            if "text" in choice:
                return choice["text"]

        raise ValueError("Unable to extract content from response")

    def extract_json_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and parse JSON from an API response.

        Args:
            response: The API response dictionary

        Returns:
            Parsed JSON as a dictionary
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
        try:
            encoding = tiktoken.encoding_for_model(self.model)
        except KeyError:
            # If model not found, use cl100k_base encoding (used by gpt-4, gpt-3.5-turbo)
            encoding = tiktoken.get_encoding("cl100k_base")

        return len(encoding.encode(text))

    def set_model(self, model: str) -> None:
        """Change the model being used.

        Args:
            model: New model name to use
        """
        self.model = model

    def get_model(self) -> str:
        """Get the current model name.

        Returns:
            Current model name
        """
        return self.model

    def get_context_limit(self) -> int:
        """Get the maximum context length (in tokens) for the current model.

        Returns:
            Maximum context length in tokens
        """
        # Model context limits (as of 2026)
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

            # GPT-5 (future-proofing)
            "gpt-5": 128000,
        }

        # Try exact match first
        if self.model in context_limits:
            return context_limits[self.model]

        # Try prefix matching for versioned models
        for model_prefix, limit in context_limits.items():
            if self.model.startswith(model_prefix):
                return limit

        # Default to conservative limit if model not found
        return 8192
