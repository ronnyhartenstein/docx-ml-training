#!/usr/bin/env python3
"""
Phase 1: DOCX-Dateien extrahieren und als JSON speichern.

Verwendung:
  python scripts/1_extract.py                   # verarbeitet data/raw/
  python scripts/1_extract.py path/to/docs/     # custom Verzeichnis
  python scripts/1_extract.py file.docx         # einzelne Datei
"""
import json
import sys
from pathlib import Path

from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from extraction import DocxExtractor, Chunker


def extract_file(filepath: Path, extractor: DocxExtractor, chunker: Chunker) -> dict:
    doc = extractor.extract(filepath)
    chunks = chunker.chunk_document(doc)

    return {
        "filename": filepath.name,
        "filepath": str(filepath),
        "metadata": {
            "module": doc.filename_meta.module,
            "release": doc.filename_meta.release,
            "doc_version": doc.filename_meta.doc_version,
            "doc_type": doc.filename_meta.doc_type,
            "ticket_id": doc.filename_meta.ticket_id,
            "parsed_with_fallback": doc.filename_meta.parsed_with_fallback,
        },
        "sections": [
            {"heading": s.heading, "level": s.level, "text": s.text}
            for s in doc.sections
        ],
        "chunks": [
            {
                "text": c.text,
                "section_heading": c.section_heading,
                "chunk_index": c.chunk_index,
                "total_chunks": c.total_chunks,
            }
            for c in chunks
        ],
        "chunk_count": len(chunks),
    }


def main():
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else settings.raw_docs_dir
    output_dir = settings.extracted_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    extractor = DocxExtractor()
    chunker = Chunker(chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)

    if target.is_file():
        docx_files = [target]
    else:
        docx_files = sorted(target.rglob("*.docx"))

    if not docx_files:
        print(f"Keine DOCX-Dateien gefunden in: {target}")
        sys.exit(1)

    print(f"Verarbeite {len(docx_files)} Datei(en)...")
    errors = []

    for filepath in tqdm(docx_files, unit="Datei"):
        out_path = output_dir / (filepath.stem + ".json")
        try:
            data = extract_file(filepath, extractor, chunker)
            out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            errors.append((filepath.name, str(e)))
            tqdm.write(f"  FEHLER {filepath.name}: {e}")

    print(f"\nErgebnis: {len(docx_files) - len(errors)} OK, {len(errors)} Fehler")
    print(f"Output: {output_dir.resolve()}")

    if errors:
        print("\nFehler-Details:")
        for name, err in errors:
            print(f"  {name}: {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()
