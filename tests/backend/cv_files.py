"""Build small, fictional CV files (PDF, DOCX) in memory for the tests."""

from __future__ import annotations

import io
import zipfile
from xml.sax.saxutils import escape

FIRST_CV = """Camille Exemple
Élève ingénieure data et IA
camille.exemple@example.com · 06 00 00 00 00 · linkedin.com/in/camille-exemple-fictif

Expériences
Stagiaire data scientist — Assurance Exemple (2026-04 – 2026-08)
- Conçu un modèle de détection de fraude qui a augmenté le rappel de 18 %
- Automatisé la préparation des données

Formation
Diplôme d'ingénieur — École d'ingénieurs Exemple (2024-09 – 2027-09)

Compétences
Langages : Python, SQL
Outils : Git, Docker

Langues
Anglais : TOEIC 945
"""

SECOND_CV = """Camille Exemple
Data scientist junior
camille.exemple@example.com

Expériences
Stagiaire Data Scientist — assurance exemple (2026-04 – 2026-08)
- Conçu un modèle de détection de fraude qui a augmenté le rappel de 18 %
- Présenté les résultats au comité de direction
Assistante de recherche — Laboratoire Exemple (2025-06 – 2025-08)
- Annoté un corpus de 12 000 décisions

Projets
Bot de veille (2025)
- 300 utilisateurs actifs

Compétences
Langages : python, R

Langues
anglais : TOEIC 945
Espagnol : B1
"""


def make_pdf(pages: list[str]) -> bytes:
    """A valid PDF with one Helvetica text block per page (WinAnsi, so accents work)."""
    objects: list[bytes] = []
    page_ids: list[int] = []
    font_id = 3
    next_id = 4
    contents: list[tuple[int, int, bytes]] = []
    for text in pages:
        lines = text.splitlines() or [""]
        ops = ["BT", "/F1 10 Tf", "12 TL", "40 800 Td"]
        for line in lines:
            safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            safe = safe.replace("—", "-").replace("–", "-").replace("·", "-")
            ops.append(f"({safe}) Tj T*")
        ops.append("ET")
        stream = "\n".join(ops).encode("cp1252", errors="replace") if text else b""
        page_id, content_id = next_id, next_id + 1
        next_id += 2
        page_ids.append(page_id)
        contents.append((page_id, content_id, stream))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode())
    objects.append(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    )
    for page_id, content_id, stream in contents:
        assert page_id == len(objects) + 1
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>".encode()
        )
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        out.write(f"{offset:010d} 00000 n \n".encode())
    out.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return out.getvalue()


def make_docx(paragraphs: list[str], link: tuple[str, str] | None = None) -> bytes:
    """A minimal DOCX; `link` = (label, url) adds a hyperlink paragraph and a table."""
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    body = "".join(
        f'<w:p><w:r><w:t xml:space="preserve">{escape(p)}</w:t></w:r></w:p>' for p in paragraphs
    )
    rels = ""
    if link:
        body += (
            f'<w:p><w:hyperlink r:id="rId9"><w:r><w:t>{escape(link[0])}</w:t></w:r>'
            "</w:hyperlink></w:p>"
            "<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Cellule A</w:t></w:r><w:r><w:tab/>"
            "<w:t>suite</w:t></w:r></w:p></w:tc></w:tr></w:tbl>"
        )
        rels = (
            '<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/'
            f'2006/relationships/hyperlink" Target="{escape(link[1])}" TargetMode="External"/>'
        )
    document = (
        f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="{w}" xmlns:r="{r}">'
        f"<w:body>{body}</w:body></w:document>"
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.'
        f'openxmlformats.org/package/2006/relationships">{rels}</Relationships>'
    )
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("word/document.xml", document)
        archive.writestr("word/_rels/document.xml.rels", rels_xml)
    return out.getvalue()
