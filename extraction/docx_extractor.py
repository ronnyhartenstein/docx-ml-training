"""
Extrahiert strukturierten Text aus DOCX-Dateien.
Verarbeitet Absätze und Tabellen in Dokumentreihenfolge.
"""
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from .filename_parser import FilenameParser, FilenameMeta


@dataclass
class Section:
    heading: str
    level: int        # 1 = Heading1, 0 = kein Heading
    text: str


@dataclass
class DocumentContent:
    filepath: str
    filename_meta: FilenameMeta
    sections: list[Section] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        parts = []
        for s in self.sections:
            if s.heading:
                parts.append(f"\n## {s.heading}\n")
            parts.append(s.text)
        return "\n".join(parts)


class DocxExtractor:
    _parser = FilenameParser()

    # Word-Stilnamen, die Überschriften sind
    _HEADING_STYLES = {
        "heading 1": 1, "heading 2": 2, "heading 3": 3,
        "heading 4": 4, "heading 5": 5, "heading 6": 6,
        "überschrift 1": 1, "überschrift 2": 2, "überschrift 3": 3,
    }

    def extract(self, filepath: str | Path) -> DocumentContent:
        filepath = Path(filepath)
        doc = Document(str(filepath))
        meta = self._parser.parse(filepath)
        content = DocumentContent(filepath=str(filepath), filename_meta=meta)

        current_heading = ""
        current_level = 0
        current_text_parts: list[str] = []

        def flush_section():
            text = "\n".join(current_text_parts).strip()
            if text or current_heading:
                content.sections.append(
                    Section(heading=current_heading, level=current_level, text=text)
                )
            current_text_parts.clear()

        body = doc.element.body
        for child in body:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

            if tag == "p":
                para = Paragraph(child, doc)
                style_name = (para.style.name or "").lower()
                heading_level = self._HEADING_STYLES.get(style_name, 0)

                if heading_level > 0:
                    flush_section()
                    current_heading = para.text.strip()
                    current_level = heading_level
                else:
                    text = para.text.strip()
                    if text:
                        current_text_parts.append(text)

            elif tag == "tbl":
                table = Table(child, doc)
                table_text = self._format_table(table)
                if table_text:
                    current_text_parts.append(table_text)

        flush_section()
        return content

    def _format_table(self, table: Table) -> str:
        rows = []
        for i, row in enumerate(table.rows):
            cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
            rows.append(" | ".join(cells))
            if i == 0 and len(table.rows) > 1:
                rows.append("-" * max(len(r) for r in rows))
        if not rows:
            return ""
        return "TABELLE:\n" + "\n".join(rows)
