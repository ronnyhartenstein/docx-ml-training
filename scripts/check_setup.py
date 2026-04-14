#!/usr/bin/env python3
"""
Prüft, ob alle Voraussetzungen für das PPS neo Fine-Tuning-System erfüllt sind.

Verwendung:
  python scripts/check_setup.py
"""
import importlib
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def check(label: str, ok: bool, hint: str = ""):
    status = "✓" if ok else "✗"
    print(f"  [{status}] {label}")
    if not ok and hint:
        print(f"       → {hint}")
    return ok


def main():
    all_ok = True
    print("=== PPS neo Setup-Check ===\n")

    # Python-Pakete
    print("Python-Pakete:")
    required = {
        "mlx_lm": "pip install mlx-lm",
        "docx": "pip install python-docx",
        "tiktoken": "pip install tiktoken",
        "httpx": "pip install httpx",
        "fastapi": "pip install fastapi",
        "uvicorn": "pip install uvicorn[standard]",
        "pydantic_settings": "pip install pydantic-settings",
    }
    for module, install_hint in required.items():
        try:
            importlib.import_module(module)
            ok = True
        except ImportError:
            ok = False
        if not check(module, ok, install_hint):
            all_ok = False

    # Ollama
    print("\nOllama:")
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=5.0)
        ollama_ok = response.status_code == 200
        models = [m["name"] for m in response.json().get("models", [])]
    except Exception:
        ollama_ok = False
        models = []

    if not check("Ollama läuft", ollama_ok, "brew install ollama && ollama serve"):
        all_ok = False
    else:
        qa_model = "llama3.1:8b"
        model_ok = any(qa_model in m for m in models)
        if not check(f"Modell {qa_model}", model_ok, f"ollama pull {qa_model}"):
            all_ok = False

    # MLX Platform (Apple Silicon)
    print("\nHardware:")
    try:
        import mlx.core as mx
        device_info = str(mx.default_device())
        metal_ok = "gpu" in device_info.lower() or "metal" in device_info.lower()
        check(f"Apple Silicon / Metal ({device_info})", metal_ok)
    except Exception:
        check("Apple Silicon / Metal", False, "mlx-lm benötigt Apple Silicon")

    # Verzeichnisse
    print("\nVerzeichnisse:")
    dirs = ["data/raw", "data/extracted", "data/training", "models"]
    for d in dirs:
        p = Path(d)
        if not check(str(p), p.exists()):
            p.mkdir(parents=True, exist_ok=True)
            print(f"       → Erstellt: {p}")

    # Konfiguration
    print("\nKonfiguration:")
    check(".env vorhanden", Path(".env").exists(), "cp .env.example .env (oder .env manuell erstellen)")

    print()
    if all_ok:
        print("Alles bereit! Nächster Schritt:")
        print("  1. DOCX-Dateien nach data/raw/ kopieren")
        print("  2. python scripts/1_extract.py")
    else:
        print("Einige Voraussetzungen fehlen (siehe ✗ oben).")
        sys.exit(1)


if __name__ == "__main__":
    main()
