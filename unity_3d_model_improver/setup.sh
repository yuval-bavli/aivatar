#!/usr/bin/env bash
# setup.sh — One-time setup for the Unity 3D Model Improver
#
# What it does:
#   1. Detects / installs Ollama
#   2. Pulls the required vision models via Ollama (stored in Ollama's default location)
#   3. Creates / activates the Python virtual environment in ../.venv
#   4. Installs Python dependencies
#
# GPU requirement:
#   Primary model  : qwen3-vl:8b  (~6 GB VRAM)  — NVIDIA GPU strongly recommended
#   Fallback model : qwen2.5vl:7b (~5 GB VRAM)  — used automatically on OOM
#   Minimum GPU    : 8 GB VRAM (e.g. RTX 3070 / 4060 Ti)
#   Recommended    : 12 GB VRAM (e.g. RTX 4070 Ti) for comfortable headroom
#
#   CPU-only is possible but inference will be very slow (~10–30× slower).
#   Ollama manages VRAM automatically — no manual configuration needed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"
MODELS_DIR="$SCRIPT_DIR/ai_models"

PRIMARY_MODEL="qwen3-vl:8b"
FALLBACK_MODEL="qwen2.5vl:7b"

echo "========================================"
echo "  Aivatar 3D Model Improver — Setup"
echo "========================================"
echo "Repo root:  $REPO_ROOT"
echo "venv:       $VENV_DIR"
echo "AI models:  Ollama default location (run 'ollama list' to see)"
echo ""

# ── Step 1: Ollama ─────────────────────────────────────────────────────────
echo "[1/4] Checking Ollama …"

if command -v ollama &>/dev/null; then
    OLLAMA_VERSION=$(ollama --version 2>/dev/null | head -1 || echo "unknown")
    echo "  ✓ Ollama already installed: $OLLAMA_VERSION"
else
    echo "  Ollama not found. Installing …"

    if [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]] || [[ -n "${WINDIR:-}" ]]; then
        # Windows (Git Bash / MSYS2)
        echo "  Detected Windows. Attempting install via winget …"
        if command -v winget &>/dev/null; then
            winget install --id Ollama.Ollama -e --silent || {
                echo "  winget install failed. Please download manually from https://ollama.com/download"
                echo "  Then re-run this script."
                exit 1
            }
            # Refresh PATH
            export PATH="$PATH:/c/Users/$USERNAME/AppData/Local/Programs/Ollama"
        else
            echo "  winget not available."
            echo "  Please install Ollama manually from https://ollama.com/download/windows"
            echo "  Then re-run this script."
            exit 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &>/dev/null; then
            brew install ollama
        else
            curl -fsSL https://ollama.com/install.sh | sh
        fi
    else
        # Linux
        curl -fsSL https://ollama.com/install.sh | sh
    fi

    echo "  ✓ Ollama installed."
fi

# Ensure Ollama server is running
echo ""
echo "[2/4] Starting Ollama server (if not already running) …"
if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
    echo "  Starting ollama serve in background …"
    ollama serve &>/dev/null &
    OLLAMA_PID=$!
    echo "  Waiting for server to be ready …"
    for i in $(seq 1 20); do
        if curl -s http://localhost:11434/api/tags &>/dev/null; then
            echo "  ✓ Ollama server is up."
            break
        fi
        sleep 1
    done
    if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
        echo "  ERROR: Ollama server did not start. Please run 'ollama serve' manually."
        exit 1
    fi
else
    echo "  ✓ Ollama server already running."
fi

# ── Step 2: Pull models ─────────────────────────────────────────────────────
echo ""
echo "[3/4] Pulling AI vision models …"
echo "  Primary : $PRIMARY_MODEL  (~6 GB download, ~6 GB VRAM)"
echo "  Fallback: $FALLBACK_MODEL (~5 GB download, ~5 GB VRAM)"
echo "  Models are stored in Ollama's default location."
echo "  Note: qwen3-vl requires 'think: False' in API calls to suppress"
echo "        chain-of-thought output — audit.py handles this automatically."

pull_model() {
    local model="$1"
    echo ""
    echo "  Pulling $model …"
    if ollama list 2>/dev/null | grep -q "^${model%:*}"; then
        echo "  ✓ $model already present."
    else
        if ollama pull "$model"; then
            echo "  ✓ $model pulled successfully."
        else
            echo "  ⚠ WARNING: Failed to pull $model."
            echo "    Check available models: https://ollama.com/library"
        fi
    fi
}

pull_model "$PRIMARY_MODEL"
pull_model "$FALLBACK_MODEL"

# ── Step 3: Python venv ────────────────────────────────────────────────────
echo ""
echo "[4/4] Setting up Python virtual environment …"

if [ ! -d "$VENV_DIR" ]; then
    echo "  Creating venv at $VENV_DIR …"
    python -m venv "$VENV_DIR"
    echo "  ✓ venv created."
else
    echo "  ✓ venv already exists at $VENV_DIR"
fi

# Activate
if [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]] || [[ -n "${WINDIR:-}" ]]; then
    ACTIVATE="$VENV_DIR/Scripts/activate"
else
    ACTIVATE="$VENV_DIR/bin/activate"
fi

source "$ACTIVATE"
echo "  ✓ venv activated"

echo "  Installing Python dependencies …"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
echo "  ✓ Dependencies installed."

# ── Done ───────────────────────────────────────────────────────────────────
echo ""
echo "========================================"
echo "  Setup complete!"
echo "========================================"
echo ""
echo "Installed models:"
ollama list 2>/dev/null | grep -E "^(qwen3-vl|qwen2\.5vl)" || echo "  (none yet — pull may still be in progress)"
echo ""
echo "To run the audit (Claude drives the improvement loop):"
echo "  1. Open Unity with the avatar scene"
echo "  2. cd $SCRIPT_DIR"
if [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]] || [[ -n "${WINDIR:-}" ]]; then
    echo "  3. source $VENV_DIR/Scripts/activate"
else
    echo "  3. source $VENV_DIR/bin/activate"
fi
echo "  4. python audit.py"
echo ""
echo "Optional flags:"
echo "  --ref /path/to/reference.png   Override reference photo (default: 3d_model_desired.png)"
echo ""
echo "Troubleshooting:"
echo "  - 'Cannot connect to Ollama' → run: ollama serve"
echo "  - OOM on qwen3-vl:8b → script auto-falls back to qwen2.5vl:7b"
echo "  - Empty model response → ensure think:False is set (already in audit.py)"
echo ""
