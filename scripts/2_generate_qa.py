#!/usr/bin/env python3
"""
Phase 2: Q&A-Trainingsdaten aus extrahierten Chunks generieren.

Verwendung:
  python scripts/2_generate_qa.py              # verarbeitet data/extracted/
  python scripts/2_generate_qa.py --limit 10  # nur 10 Chunks (zum Testen)
  python scripts/2_generate_qa.py --resume    # überspringt bereits generierte Dateien
"""
import argparse
import json
import sys
from pathlib import Path

from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from training_data import QAGenerator, DatasetBuilder, QAPair


def load_all_chunks(extracted_dir: Path) -> list[dict]:
    chunks = []
    for json_file in sorted(extracted_dir.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            meta = data.get("metadata", {})
            for chunk in data.get("chunks", []):
                chunk["source_file"] = data["filename"]
                chunk["module"] = meta.get("module", "")
                chunk["release"] = meta.get("release", "")
                chunk["doc_version"] = meta.get("doc_version", "")
                chunks.append(chunk)
        except Exception as e:
            tqdm.write(f"  Überspringe {json_file.name}: {e}")
    return chunks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Maximale Chunk-Anzahl")
    parser.add_argument("--resume", action="store_true", help="Bereits verarbeitete überspringen")
    args = parser.parse_args()

    extracted_dir = settings.extracted_dir
    if not extracted_dir.exists():
        print(f"Fehler: {extracted_dir} existiert nicht. Erst scripts/1_extract.py ausführen.")
        sys.exit(1)

    print("Lade Chunks...")
    all_chunks = load_all_chunks(extracted_dir)
    if not all_chunks:
        print("Keine Chunks gefunden.")
        sys.exit(1)

    if args.limit:
        all_chunks = all_chunks[: args.limit]

    print(f"Verarbeite {len(all_chunks)} Chunks ({settings.qa_per_chunk} Q&A pro Chunk)...")
    print(f"Erwartete Q&A-Paare: ~{len(all_chunks) * settings.qa_per_chunk}")

    training_dir = settings.training_dir
    training_dir.mkdir(parents=True, exist_ok=True)

    all_pairs: list[QAPair] = []
    errors = 0

    with QAGenerator(
        ollama_base_url=settings.ollama_base_url,
        model=settings.qa_generator_model,
        qa_per_chunk=settings.qa_per_chunk,
    ) as generator:
        for chunk in tqdm(all_chunks, unit="Chunk"):
            try:
                pairs = generator.generate_from_chunk(chunk)
                all_pairs.extend(pairs)
            except Exception as e:
                tqdm.write(f"  FEHLER bei Chunk: {e}")
                errors += 1

    if not all_pairs:
        print("Keine Q&A-Paare generiert.")
        sys.exit(1)

    print(f"\nGeneriert: {len(all_pairs)} Q&A-Paare ({errors} Fehler)")

    builder = DatasetBuilder(training_dir, train_split=settings.train_split)
    train_count, valid_count = builder.build(all_pairs)

    print(f"train.jsonl: {train_count} Einträge")
    print(f"valid.jsonl: {valid_count} Einträge")
    print(f"Output: {training_dir.resolve()}")


if __name__ == "__main__":
    main()
