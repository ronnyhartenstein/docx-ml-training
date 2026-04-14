#!/usr/bin/env bash
# Phase 5: Fine-Tuned Modell als OpenAI-kompatibler Server bereitstellen
#
# Verwendung:
#   bash scripts/5_serve.sh
#   bash scripts/5_serve.sh --adapter-path ./models/adapters  # Adapter ohne Fusion
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_DIR/.env" ]; then
  export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

FINETUNED_MODEL="${FINETUNED_MODEL_PATH:-./models/ppsneo-finetuned}"
PORT="${MLX_SERVER_PORT:-8080}"

# Fallback auf Basismodell + Adapter wenn fusioniertes Modell nicht existiert
if [ ! -d "$FINETUNED_MODEL" ] || [ -z "$(ls -A "$FINETUNED_MODEL" 2>/dev/null)" ]; then
  BASE_MODEL="${BASE_MODEL_PATH:-./models/llama3.1-8b-base}"
  ADAPTER_PATH="${ADAPTER_PATH:-./models/adapters}"
  echo "Fusioniertes Modell nicht gefunden → starte mit Adapter"
  echo "Modell: $BASE_MODEL + Adapter: $ADAPTER_PATH"
  SERVE_CMD="python -m mlx_lm.server --model $BASE_MODEL --adapter-path $ADAPTER_PATH --port $PORT $@"
else
  echo "Modell: $FINETUNED_MODEL"
  SERVE_CMD="python -m mlx_lm.server --model $FINETUNED_MODEL --port $PORT $@"
fi

echo "=== PPS neo Modell-Server ==="
echo "Port: $PORT"
echo "API: http://localhost:$PORT/v1/chat/completions"
echo "Web UI: http://localhost:${API_PORT:-8000}"
echo ""
echo "Server starten... (Ctrl+C zum Beenden)"
echo ""

eval "$SERVE_CMD"
