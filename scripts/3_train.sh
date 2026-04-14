#!/usr/bin/env bash
# Phase 3: LoRA Fine-Tuning mit MLX-LM
#
# Voraussetzungen:
#   - data/training/train.jsonl und valid.jsonl existieren
#   - models/llama3.1-8b-base/ enthält das Basismodell
#   - mlx-lm ist installiert (pip install mlx-lm)
#
# Verwendung:
#   bash scripts/3_train.sh
#   bash scripts/3_train.sh --iters 500   # schneller Test
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Konfiguration (aus .env lesen falls vorhanden)
if [ -f "$PROJECT_DIR/.env" ]; then
  export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
fi

BASE_MODEL="${BASE_MODEL_PATH:-./models/llama3.1-8b-base}"
ADAPTER_PATH="${ADAPTER_PATH:-./models/adapters}"
DATA_DIR="./data/training"

echo "=== PPS neo Fine-Tuning ==="
echo "Basismodell: $BASE_MODEL"
echo "Adapter-Ausgabe: $ADAPTER_PATH"
echo "Trainingsdaten: $DATA_DIR"
echo ""

# Prüfen ob Trainingsdaten vorhanden
if [ ! -f "$DATA_DIR/train.jsonl" ]; then
  echo "FEHLER: $DATA_DIR/train.jsonl nicht gefunden."
  echo "Bitte zuerst: python scripts/2_generate_qa.py"
  exit 1
fi

TRAIN_COUNT=$(wc -l < "$DATA_DIR/train.jsonl")
VALID_COUNT=$(wc -l < "$DATA_DIR/valid.jsonl" 2>/dev/null || echo 0)
echo "Trainings-Einträge: $TRAIN_COUNT"
echo "Validierungs-Einträge: $VALID_COUNT"
echo ""

mkdir -p "$ADAPTER_PATH"

python -m mlx_lm.lora \
  --model "$BASE_MODEL" \
  --train \
  --data "$DATA_DIR" \
  --batch-size 4 \
  --grad-checkpoint \
  --iters 2000 \
  --steps-per-eval 100 \
  --val-batches 25 \
  --learning-rate 1e-5 \
  --lora-layers 16 \
  --adapter-path "$ADAPTER_PATH" \
  "$@"

echo ""
echo "=== Training abgeschlossen ==="
echo "Adapter gespeichert: $ADAPTER_PATH"
echo "Nächster Schritt: bash scripts/4_fuse.sh"
