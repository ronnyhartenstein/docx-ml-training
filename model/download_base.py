#!/usr/bin/env python3
"""
Lädt das Basis-Modell von HuggingFace herunter und konvertiert es ins MLX-Format.

Verwendung:
  python model/download_base.py
  python model/download_base.py --model mlx-community/Llama-3.1-8B-Instruct-4bit
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings

# Vorkonvertierte MLX-Modelle von mlx-community (empfohlen — kein eigener Konvertierungsschritt)
RECOMMENDED_MODELS = {
    "llama3.1-8b": "mlx-community/Meta-Llama-3.1-8B-Instruct-4bit",
    "llama3.2-3b": "mlx-community/Llama-3.2-3B-Instruct-4bit",
    "qwen2.5-14b": "mlx-community/Qwen2.5-14B-Instruct-4bit",
    "mistral-7b": "mlx-community/Mistral-7B-Instruct-v0.3-4bit",
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        default=RECOMMENDED_MODELS["llama3.1-8b"],
        help=f"HuggingFace-Modell-ID oder Kurzname {list(RECOMMENDED_MODELS.keys())}",
    )
    args = parser.parse_args()

    model_id = RECOMMENDED_MODELS.get(args.model, args.model)
    output_path = Path(settings.base_model_path)

    if output_path.exists() and any(output_path.iterdir()):
        print(f"Modell bereits vorhanden: {output_path}")
        print("Zum Neuherunterladen Verzeichnis löschen.")
        return

    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Lade Modell: {model_id}")
    print(f"Ziel: {output_path.resolve()}")
    print("(Dies kann je nach Internetverbindung einige Minuten dauern...)\n")

    cmd = [
        sys.executable, "-m", "mlx_lm.convert",
        "--hf-path", model_id,
        "--mlx-path", str(output_path),
    ]

    # mlx-community Modelle sind bereits konvertiert → kein -q Flag nötig
    if "mlx-community" not in model_id:
        cmd += ["-q", "--q-bits", "4"]

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("Fehler beim Herunterladen.")
        sys.exit(1)

    print(f"\nModell gespeichert: {output_path.resolve()}")
    print(f"Nächster Schritt: python scripts/2_generate_qa.py")


if __name__ == "__main__":
    main()
