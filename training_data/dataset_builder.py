"""
Wandelt Q&A-Paare in das MLX-LM Chat-Format (JSONL) um
und erstellt train.jsonl / valid.jsonl mit 80/20-Split.
"""
import json
import random
from pathlib import Path

from .qa_generator import QAPair
from .prompt_templates import INFERENCE_SYSTEM_PROMPT


class DatasetBuilder:
    def __init__(self, output_dir: str | Path, train_split: float = 0.8, seed: int = 42):
        self.output_dir = Path(output_dir)
        self.train_split = train_split
        self.seed = seed

    def build(self, pairs: list[QAPair]) -> tuple[int, int]:
        """Schreibt train.jsonl + valid.jsonl. Gibt (train_count, valid_count) zurück."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        records = [self._to_record(p) for p in pairs]
        random.seed(self.seed)
        random.shuffle(records)

        split_idx = int(len(records) * self.train_split)
        train_records = records[:split_idx]
        valid_records = records[split_idx:]

        self._write_jsonl(self.output_dir / "train.jsonl", train_records)
        self._write_jsonl(self.output_dir / "valid.jsonl", valid_records)

        return len(train_records), len(valid_records)

    def append_pair(self, pair: QAPair, split: str = "train"):
        """Fügt ein einzelnes Q&A-Paar direkt an die JSONL-Datei an (für Streaming-Betrieb)."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        target = self.output_dir / f"{split}.jsonl"
        record = self._to_record(pair)
        with target.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _to_record(self, pair: QAPair) -> dict:
        return {
            "messages": [
                {"role": "system", "content": INFERENCE_SYSTEM_PROMPT},
                {"role": "user", "content": pair.question},
                {"role": "assistant", "content": pair.answer},
            ]
        }

    def _write_jsonl(self, path: Path, records: list[dict]):
        with path.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
