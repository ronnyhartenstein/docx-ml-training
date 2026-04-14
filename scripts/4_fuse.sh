#!/usr/bin/env bash
# Phase 4: LoRA-Adapter in Basismodell fusionieren
#
# Verwendung:
#   bash scripts/4_fuse.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ -f "$PROJECT_DIR/.env" ]; then
  export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

BASE_MODEL="${BASE_MODEL_PATH:-./models/llama3.1-8b-base}"
ADAPTER_PATH="${ADAPTER_PATH:-./models/adapters}"
OUTPUT_PATH="${FINETUNED_MODEL_PATH:-./models/ppsneo-finetuned}"

echo "=== Adapter fusionieren ==="
echo "Basismodell: $BASE_MODEL"
echo "Adapter: $ADAPTER_PATH"
echo "Ausgabe: $OUTPUT_PATH"
echo ""

if [ ! -d "$ADAPTER_PATH" ] || [ -z "$(ls -A "$ADAPTER_PATH" 2>/dev/null)" ]; then
  echo "FEHLER: Adapter-Verzeichnis leer oder nicht vorhanden: $ADAPTER_PATH"
  echo "Bitte zuerst: bash scripts/3_train.sh"
  exit 1
fi

mkdir -p "$OUTPUT_PATH"

python -m mlx_lm.fuse \
  --model "$BASE_MODEL" \
  --adapter-path "$ADAPTER_PATH" \
  --save-path "$OUTPUT_PATH"

echo ""
echo "=== Fusionierung abgeschlossen ==="
echo "Fine-Tuned Modell gespeichert: $OUTPUT_PATH"
echo "Nächster Schritt: bash scripts/5_serve.sh"
