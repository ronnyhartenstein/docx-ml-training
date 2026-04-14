"""
Generiert Q&A-Paare aus extrahierten Chunks via Ollama.
"""
import json
import re
from dataclasses import dataclass

import httpx

from .prompt_templates import QA_GENERATION_SYSTEM, QA_GENERATION_USER


@dataclass
class QAPair:
    question: str
    answer: str
    source_file: str
    module: str
    release: str
    doc_version: str
    section_heading: str
    chunk_index: int


class QAGenerator:
    def __init__(self, ollama_base_url: str, model: str, qa_per_chunk: int = 3):
        self.ollama_base_url = ollama_base_url.rstrip("/")
        self.model = model
        self.qa_per_chunk = qa_per_chunk
        self._client = httpx.Client(timeout=120.0)

    def generate_from_chunk(self, chunk: dict) -> list[QAPair]:
        """Generiert Q&A-Paare aus einem einzelnen Chunk-Dict (aus extracted JSON)."""
        chunk_text = chunk.get("text", "").strip()
        if len(chunk_text) < 100:
            return []

        prompt = QA_GENERATION_USER.format(
            n=self.qa_per_chunk,
            module=chunk.get("module", ""),
            release=chunk.get("release", ""),
            section_heading=chunk.get("section_heading", ""),
            chunk_text=chunk_text,
        )

        try:
            raw_json = self._call_ollama(prompt)
            pairs_raw = self._parse_json(raw_json)
        except Exception:
            return []

        results = []
        for item in pairs_raw:
            frage = item.get("frage", "").strip()
            antwort = item.get("antwort", "").strip()
            if frage and antwort:
                results.append(QAPair(
                    question=frage,
                    answer=antwort,
                    source_file=chunk.get("source_file", ""),
                    module=chunk.get("module", ""),
                    release=chunk.get("release", ""),
                    doc_version=chunk.get("doc_version", ""),
                    section_heading=chunk.get("section_heading", ""),
                    chunk_index=chunk.get("chunk_index", 0),
                ))
        return results

    def _call_ollama(self, user_prompt: str) -> str:
        response = self._client.post(
            f"{self.ollama_base_url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": QA_GENERATION_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.3},
            },
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    def _parse_json(self, text: str) -> list[dict]:
        # JSON-Array aus der Antwort extrahieren (LLMs fügen manchmal Text davor/dahinter ein)
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if not match:
            raise ValueError("Kein JSON-Array in Antwort gefunden")
        return json.loads(match.group())

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
