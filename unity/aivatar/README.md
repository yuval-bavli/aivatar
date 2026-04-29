# unity/aivatar

Unity project for the Aivatar 3D talking head with real-time lip sync.

**Unity version:** 2022.3 LTS (URP)

## First-time setup

1. Open this folder in Unity Hub.
2. Ensure `.env` at the repo root contains `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` (read automatically by `EnvLoader.cs` on domain reload).
3. Run menu **Aivatar > Setup Avatar Scene** once to wire the scene (Avatar + ConversationManager + Stop button).
4. Start the Python servers (TTS, STT, orchestrator) — see the root [CLAUDE.md](../../CLAUDE.md).
5. Press **Play**. The avatar greets you; speak into the mic to continue the conversation.

## Assets layout

```
Assets/
├── Scripts/          — Runtime C# (conversation client, lip sync, UI)
├── Editor/           — Editor-only C# (scene setup, env loading, diagnostics)
├── Data/Mappings/    — VisemeMapping ScriptableObjects (Azure ID → blendshape name)
├── Models/Avatar/    — 3D avatar mesh, materials, textures, viseme animation clip
├── Images/           — UI textures (microphone icon)
├── Packages/         — NuGet DLLs (Azure SDK, Newtonsoft.Json, etc.)
├── Plugins/          — Native plugins
├── Shaders/          — Custom HLSL shaders
└── Settings/         — URP renderer and quality settings
```

## Key runtime scripts

| Script | Role |
|--------|------|
| `ConversationClient.cs` | WebSocket client to the orchestrator (port 5124); drives the full conversation loop |
| `AnimClipLipSync.cs` | Active lip-sync controller; plays Azure visemes against a pre-baked animation clip |
| `LipSyncBase.cs` | Abstract base referenced by `ConversationClient.lipSyncController` |
| `AudioVisemeDecoder.cs` | Decodes base64 WAV from server into `AudioClip` + `VisemeTimeline` |
| `VisemeTimeline.cs` / `VisemeEvent.cs` | Timeline data structures shared between decoder and lip-sync |
| `VisemeMapping.cs` | ScriptableObject mapping Azure viseme IDs (0–14) to blendshape names |
| `StopButtonUI.cs` | Wires a uGUI Button to `ConversationClient.Stop()` |
| `MicrophoneIndicatorUI.cs` | Visual mic-active indicator |
| `AivatarLogger.cs` | Forwards Unity logs to `debug/logs/unity/` |
| `AzureSpeechManager.cs` + `TestSpeak.cs` | Legacy direct-TTS smoke-test path (bypasses orchestrator; not used in production) |

## Key editor scripts

| Script | Role |
|--------|------|
| `SetupAvatarScene.cs` | Menu **Aivatar > Setup Avatar Scene**: creates and wires all GameObjects |
| `EnvLoader.cs` | Reads `.env` at repo root; injects credentials into `PlayerPrefs` on domain reload |
| `BlendShapeInspector.cs` | Custom inspector for browsing blendshape names on a mesh |
| `LipSyncFrameRecorder.cs` | Captures per-frame PNGs during a lip-sync run for debugging |
| `LipSyncValidator.cs` | Validates the wired-up lip-sync setup |
| `CheckSceneSetup.cs` | One-shot scene sanity check |

## Viseme pipeline

Azure TTS viseme IDs (0–14) → `VisemeMapping` ScriptableObject → `AnimClipLipSync` plays the corresponding pose from the pre-baked viseme animation clip on the avatar's `SkinnedMeshRenderer`, with look-ahead cross-fade and `SmoothDamp`.

Audio offset unit: **100-nanosecond ticks** (`ms × 10 000`). This is what the Python TTS server emits and what `AudioVisemeDecoder` expects.

## WebSocket protocol

The orchestrator listens on `ws://127.0.0.1:5124`. `ConversationClient` connects automatically on Play. Messages are JSON:

- **Server → Client:** `{ "type": "speech", "audio_base64": "...", "viseme_events": [...], "sentence_events": [...] }`
- **Client → Server:** raw 16kHz mono 16-bit PCM audio chunks (mic capture)
