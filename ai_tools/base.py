"""Abstract base class for AI text chat providers."""
import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional

from ._types import ChatConfig, ChatMessage, ChatResponse


class ChatClient(ABC):
    """
    Abstract base class for AI text chat providers.

    Maintains conversation history for multi-turn chat.
    System prompt is set at init or updated via the property.

    Usage:
        client = SomeConcreteClient(
            system_prompt="You are a helpful assistant.",
            config=ChatConfig(temperature=0.8, max_tokens=512),
        )

        # Synchronous
        response = client.send("Hello!")
        print(response.content)

        # Async
        response = await client.send_async("Hello!")

        # Streaming (async)
        async for chunk in client.stream_async("Tell me a story"):
            print(chunk, end="", flush=True)

        # Multi-turn — history is maintained automatically
        client.send("What did I just say?")

        # Reset conversation
        client.clear_history()
    """

    def __init__(
        self,
        system_prompt: str = "",
        config: Optional[ChatConfig] = None,
    ):
        self.system_prompt = system_prompt
        self.config = config or ChatConfig()
        self._history: List[ChatMessage] = []

    @property
    def history(self) -> List[ChatMessage]:
        """A copy of the current conversation history."""
        return list(self._history)

    def clear_history(self) -> None:
        """Reset conversation history (system prompt is preserved)."""
        self._history.clear()

    @abstractmethod
    async def send_async(self, message: str) -> ChatResponse:
        """
        Send a user message and receive an assistant response.
        Both the user message and assistant response are appended to history.
        """
        ...

    @abstractmethod
    async def stream_async(self, message: str) -> AsyncIterator[str]:
        """
        Send a user message and stream the assistant response token by token.
        Both the user message and the full assistant response are appended to
        history after streaming completes.
        """
        ...

    def send(self, message: str) -> ChatResponse:
        """Synchronous wrapper around send_async."""
        return asyncio.run(self.send_async(message))
