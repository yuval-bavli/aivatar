# profiles

Avatar personality profiles. Each subdirectory is a self-contained profile that configures the AI tutor's persona, teaching style, and lesson content.

## Structure

```
profiles/
└── <profile_name>/
    ├── system_prompt.md   — Claude system prompt (persona + rules)
    ├── greeting.txt       — Opening line spoken before the AI loop starts
    └── lesson_*.md        — Topic-specific vocabulary and activity scripts
```

## Selecting a profile

Set the `AVATAR_PROFILE` environment variable before starting the orchestrator:

```bash
AVATAR_PROFILE=english_tutor_heb .venv/Scripts/python -m aivatar_app
```

Default profile (when the variable is unset): `english_tutor_heb`.

## Available profiles

| Profile | Description |
|---------|-------------|
| `english_tutor_heb` | English tutor "Sunny" for Hebrew-speaking children (ages 5–9) |

## Creating a new profile

1. Create a new subdirectory under `profiles/`.
2. Add `system_prompt.md` — this is passed verbatim as the Claude system prompt.
3. Add `greeting.txt` — one or two sentences the avatar speaks before the first user turn.
4. Add any `lesson_*.md` files referenced in the system prompt.
