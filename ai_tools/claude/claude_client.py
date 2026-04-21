"""Claude (Anthropic) implementation of ChatClient."""
import os
from typing import AsyncIterator, Optional

from .._types import ChatConfig, ChatMessage, ChatResponse
from ..base import ChatClient

DEFAULT_MODEL = "claude-sonnet-4-6"


def _load_env() -> None:
    """Load .env from repo root if python-dotenv is available."""
    try:
        from dotenv import load_dotenv
        here = os.path.dirname(os.path.abspath(__file__))
        for _ in range(5):
            candidate = os.path.join(here, ".env")
            if os.path.exists(candidate):
                load_dotenv(candidate)
                return
            here = os.path.dirname(here)
    except ImportError:
        pass


_load_env()


class ClaudeChatClient(ChatClient):
    """
    Claude implementation of ChatClient using the Anthropic SDK.

    API key resolution order:
      1. `api_key` constructor argument
      2. CLAUDE_KEY environment variable / .env
      3. ANTHROPIC_API_KEY environment variable / .env

    Requires `anthropic` to be installed:
        pip install anthropic

    Example:
        client = ClaudeChatClient(
            system_prompt="You are a helpful assistant.",
            config=ChatConfig(temperature=0.8, max_tokens=512),
        )
        response = client.send("Hello!")
        print(response.content)
    """

    def __init__(
        self,
        system_prompt: str = "",
        config: Optional[ChatConfig] = None,
        api_key: Optional[str] = None,
    ):
        super().__init__(system_prompt=system_prompt, config=config)
        self._api_key = (
            api_key
            or os.environ.get("CLAUDE_KEY")
            or os.environ.get("ANTHROPIC_API_KEY", "")
        )
        if not self._api_key:
            raise ValueError(
                "Claude API key not found. "
                "Set CLAUDE_KEY (or ANTHROPIC_API_KEY) in your .env file or environment."
            )
        if not self.config.model:
            self.config.model = DEFAULT_MODEL

    def _get_async_client(self):
        """Lazy-import the Anthropic SDK and return an async client."""
        try:
            import anthropic
        except ImportError:
            raise RuntimeError(
                "anthropic is not installed. Run: pip install anthropic"
            )
        return anthropic.AsyncAnthropic(api_key=self._api_key)

    def _build_messages(self) -> list:
        """Convert internal history to the Anthropic messages format."""
        return [{"role": m.role, "content": m.content} for m in self._history]

    def _build_kwargs(self) -> dict:
        """Build the common kwargs for a messages API call."""
        kwargs: dict = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "messages": self._build_messages(),
            "temperature": self.config.temperature,
        }
        if self.config.top_p != 1.0:
            kwargs["top_p"] = self.config.top_p
        if self.system_prompt:
            kwargs["system"] = self.system_prompt
        if self.config.stop_sequences:
            kwargs["stop_sequences"] = self.config.stop_sequences
        return kwargs

    async def send_async(self, message: str) -> ChatResponse:
        """Send a user message and return the assistant response."""
        self._history.append(ChatMessage(role="user", content=message))
        client = self._get_async_client()
        response = await client.messages.create(**self._build_kwargs())
        content = response.content[0].text
        self._history.append(ChatMessage(role="assistant", content=content))
        return ChatResponse(
            content=content,
            model=response.model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            stop_reason=response.stop_reason,
        )

    async def stream_async(self, message: str) -> AsyncIterator[str]:
        """Stream the assistant response token by token."""
        self._history.append(ChatMessage(role="user", content=message))
        client = self._get_async_client()
        chunks = []
        async with client.messages.stream(**self._build_kwargs()) as stream:
            async for text in stream.text_stream:
                chunks.append(text)
                yield text
        self._history.append(ChatMessage(role="assistant", content="".join(chunks)))
