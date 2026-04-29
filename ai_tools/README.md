# ai_tools

Provider-agnostic abstraction layer for AI chat backends used by the orchestrator.

## Structure

```
ai_tools/
├── base.py        — Abstract ChatClient base class
├── _types.py      — ChatConfig, ChatMessage, ChatResponse dataclasses
└── claude/
    └── claude_client.py  — Anthropic Claude implementation
```

## ChatClient interface

`base.py` defines an abstract `ChatClient` with three call modes:

| Method | Description |
|--------|-------------|
| `send(message)` | Synchronous, blocks until full response |
| `send_async(message)` | Async coroutine |
| `stream_async(message)` | Async generator, yields tokens as they arrive |

Conversation history is maintained automatically across calls. Use `clear_history()` to reset.

## ClaudeChatClient

`claude/claude_client.py` is the only concrete implementation. It wraps the Anthropic SDK.

**API key resolution order:**
1. `api_key` constructor argument
2. `CLAUDE_KEY` environment variable / `.env`
3. `ANTHROPIC_API_KEY` environment variable / `.env`

**Default model:** `claude-sonnet-4-6`

```python
from ai_tools.claude import ClaudeChatClient
from ai_tools._types import ChatConfig

client = ClaudeChatClient(
    system_prompt="You are a helpful assistant.",
    config=ChatConfig(temperature=0.8, max_tokens=512),
)
response = client.send("Hello!")
print(response.content)
```

## Adding a new provider

Subclass `ChatClient` and implement `send_async` and `stream_async`. The `send` synchronous wrapper is provided by the base class.
