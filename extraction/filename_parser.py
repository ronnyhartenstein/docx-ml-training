"""
Extrahiert Metadaten aus PPS-neo Dateinamen.

Unterstützte Muster:
  P4123256_PPS_neo-Organisation-Fachspezifikation_EE20.4_V0.1.docx
  R22.1_V1.1.docx
  PPS_neo-Abrechnung-Fachspezifikation_EE21.0_V1.0.docx
"""
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FilenameMeta:
    filename: str
    module: str = ""
    release: str = ""
    doc_version: str = ""
    doc_type: str = ""
    ticket_id: str = ""
    parsed_with_fallback: bool = False


class FilenameParser:
    # Ticket-ID: P gefolgt von Ziffern
    _TICKET_RE = re.compile(r'^(P\d+)_', re.IGNORECASE)

    # Vollständiges PPS-Muster: PPS_neo-{Modul}-{Typ}_{Release}_V{Version}
    _FULL_RE = re.compile(
        r'PPS_neo-(?P<module>[A-Za-z0-9]+)-(?P<doc_type>[A-Za-z0-9]+)'
        r'_(?P<release>[A-Za-z0-9]+\.\d+)'
        r'_V(?P<doc_version>\d+\.\d+)',
        re.IGNORECASE,
    )

    # Kurzes Release-Muster: R{Release}_V{Version}
    _SHORT_RE = re.compile(
        r'^R(?P<release>\d+\.\d+)_V(?P<doc_version>\d+\.\d+)',
        re.IGNORECASE,
    )

    # Allgemeines Versions-Fallback
    _VERSION_RE = re.compile(r'[_-]V(\d+\.\d+)', re.IGNORECASE)
    _RELEASE_RE = re.compile(r'[_-](EE|R)(\d+\.\d+)', re.IGNORECASE)

    def parse(self, filepath: str | Path) -> FilenameMeta:
        stem = Path(filepath).stem
        filename = Path(filepath).name
        meta = FilenameMeta(filename=filename)

        # Ticket-ID extrahieren
        ticket_match = self._TICKET_RE.match(stem)
        if ticket_match:
            meta.ticket_id = ticket_match.group(1)
            stem = stem[ticket_match.end():]  # Ticket-Präfix entfernen

        # Vollständiges PPS-Muster
        full_match = self._FULL_RE.search(stem)
        if full_match:
            meta.module = full_match.group("module")
            meta.doc_type = full_match.group("doc_type")
            meta.release = full_match.group("release")
            meta.doc_version = full_match.group("doc_version")
            return meta

        # Kurzes Release-Muster (R22.1_V1.1)
        short_match = self._SHORT_RE.match(stem)
        if short_match:
            meta.release = short_match.group("release")
            meta.doc_version = short_match.group("doc_version")
            meta.parsed_with_fallback = True
            return meta

        # Fallback: einzelne Felder extrahieren
        meta.parsed_with_fallback = True
        version_match = self._VERSION_RE.search(stem)
        if version_match:
            meta.doc_version = version_match.group(1)

        release_match = self._RELEASE_RE.search(stem)
        if release_match:
            meta.release = release_match.group(2)

        # Modul: erstes Wort nach Unterstrich oder Bindestrich
        parts = re.split(r'[_-]', stem)
        if parts:
            meta.module = parts[0]

        return meta
