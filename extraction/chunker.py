"""
Teilt DocumentContent in Chunks für das Fine-Tuning auf.
Strategie: Abschnitte bevorzugt zusammenhalten, bei Überlänge an Satzgrenzen teilen.
"""
import re
from dataclasses import dataclass, field

import tiktoken

from .docx_extractor import DocumentContent, Section


@dataclass
class Chunk:
    text: str
    source_file: str
    module: str
    release: str
    doc_version: str
    doc_type: str
    section_heading: str
    chunk_index: int
    total_chunks: int   # wird nachträglich gesetzt


class Chunker:
    _SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._enc = tiktoken.get_encoding("cl100k_base")

    def chunk_document(self, doc: DocumentContent) -> list[Chunk]:
        all_chunks: list[Chunk] = []
        meta = doc.filename_meta

        for section in doc.sections:
            section_chunks = self._chunk_section(section, doc.filepath, meta)
            all_chunks.extend(section_chunks)

        # Gesamtanzahl setzen
        for i, chunk in enumerate(all_chunks):
            chunk.chunk_index = i
            chunk.total_chunks = len(all_chunks)

        return all_chunks

    def _token_count(self, text: str) -> int:
        return len(self._enc.encode(text))

    def _chunk_section(self, section: Section, filepath: str, meta) -> list[Chunk]:
        full_text = section.text
        if section.heading:
            full_text = f"{section.heading}\n\n{section.text}"

        if self._token_count(full_text) <= self.chunk_size:
            return [self._make_chunk(full_text, filepath, meta, section.heading, 0)]

        # Abschnitt zu groß → an Satzgrenzen aufteilen
        sentences = self._SENTENCE_SPLIT_RE.split(full_text)
        chunks: list[Chunk] = []
        current_tokens = 0
        current_parts: list[str] = []
        overlap_buffer: list[str] = []
        chunk_idx = 0

        for sentence in sentences:
            sentence_tokens = self._token_count(sentence)

            if current_tokens + sentence_tokens > self.chunk_size and current_parts:
                text = " ".join(current_parts)
                chunks.append(self._make_chunk(text, filepath, meta, section.heading, chunk_idx))
                chunk_idx += 1

                # Overlap: letzte Sätze in neuen Chunk übernehmen
                overlap_parts: list[str] = []
                overlap_t = 0
                for part in reversed(current_parts):
                    t = self._token_count(part)
                    if overlap_t + t > self.chunk_overlap:
                        break
                    overlap_parts.insert(0, part)
                    overlap_t += t

                current_parts = overlap_parts
                current_tokens = overlap_t

            current_parts.append(sentence)
            current_tokens += sentence_tokens

        if current_parts:
            text = " ".join(current_parts)
            chunks.append(self._make_chunk(text, filepath, meta, section.heading, chunk_idx))

        return chunks

    def _make_chunk(self, text: str, filepath: str, meta, heading: str, idx: int) -> Chunk:
        return Chunk(
            text=text.strip(),
            source_file=filepath,
            module=meta.module,
            release=meta.release,
            doc_version=meta.doc_version,
            doc_type=meta.doc_type,
            section_heading=heading,
            chunk_index=idx,
            total_chunks=0,
        )
