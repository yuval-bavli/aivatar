# Environment Setup — New Machine

Follow these steps in order when bringing up this project on a fresh machine.

---

## 1. Prerequisites

- **Docker Desktop** — for the Python servers (TTS, STT, orchestrator)
- **Unity Hub + Unity 6** — for the avatar editor
- **Python 3.11+** — only needed for local (non-Docker) dev or smoke tests
- **uv / uvx** — needed for the Unity MCP bridge (install via `curl -Ls https://astral.sh/uv/install.sh | sh`)

---

## 2. Clone & secrets

```bash
git clone <repo-url>
cd aivatar
```

Create a `.env` file at the repo root (it is gitignored):

```
CLAUDE_KEY=<your Anthropic API key>
ELEVENLABS_API_KEY=<your ElevenLabs key, or leave blank to fall back to edge-tts>
```

---

## 3. Python servers (Docker)

```bash
docker compose up -d --build
docker compose ps          # all three containers should be Up
```

Services: `tts` → port 5123 · `stt` → port 8765 · `aivatar_app` → port 5124

---

## 4. Unity project

1. Open **Unity Hub → Add project** and point it at `unity/aivatar/`.
2. Let Unity reimport everything (can take several minutes on first open).
3. Open the correct scene: **File → Open Scene → `Assets/scene1.unity`**.
   - Unity defaults to a blank untitled scene on a fresh clone because `UserSettings/` is gitignored. Always open `scene1.unity` manually.
4. Run the one-time scene setup: menu **Aivatar → Setup Avatar Scene**.

---

## 5. Unity MCP (so Claude Code can control the editor)

The MCP-for-Unity package (`com.coplaydev.unity-mcp`) is already in `Packages/manifest.json`.

### 5a. Write the Claude Code config (one-time per machine)

The file `.mcp.json` at the repo root points Claude Code at Unity's local HTTP bridge.
It should already exist in the repo — if it doesn't, create it:

```json
{
  "mcpServers": {
    "unityMCP": {
      "type": "http",
      "url": "http://127.0.0.1:8080/mcp"
    }
  }
}
```

### 5b. Start the Unity MCP bridge

Inside Unity (with the project open):

1. **Window → MCP for Unity**
2. Click **Start Bridge** (or **Auto-Setup** if prompted)
3. The status dot should turn green / show "Running"

### 5c. Reload Claude Code

In VS Code: **Cmd+Shift+P → Developer: Reload Window**

After reload, the `mcp__unityMCP__*` tools will be available to Claude.

### Verifying it works

Ask Claude to run `mcp__unityMCP__manage_scene` with `action: get_active`. If it returns the scene name (`scene1`), the bridge is up.

---

## 6. Full conversation loop

With Docker running and Unity in Play mode:

1. `docker compose up -d` (if not already running)
2. Press **Play** in Unity — the avatar greets you automatically
3. Speak into your mic; press **Esc** or the Stop button to end

Change the active profile by setting `AVATAR_PROFILE=<folder_name>` in `.env` and restarting the `aivatar_app` container.

---

## Common issues

| Symptom | Fix |
|---|---|
| Unity opens with empty scene | File → Open Scene → `Assets/scene1.unity` |
| `mcp__unityMCP__*` tools missing | Unity MCP bridge not started — do step 5b, then reload VS Code |
| Docker containers exit immediately | Check logs: `docker compose logs -f aivatar_app` — usually a missing `CLAUDE_KEY` |
| TTS falls back to edge-tts | `ELEVENLABS_API_KEY` not set or quota exceeded — expected fallback |
| STT container crashes | GPU not available on this machine; STT requires NVIDIA CUDA |
