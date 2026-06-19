from __future__ import annotations

from io import BytesIO
from textwrap import wrap
from typing import Any


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _truncate_pdf_cell(value: Any, max_chars: int) -> str:
    text = "" if value is None else str(value)
    return text if len(text) <= max_chars else text[: max_chars - 1] + "..."


def _build_table_pdf(title: str, subtitle: str, headers: list[str], rows: list[list[Any]]) -> bytes:
    page_width = 612
    page_height = 792
    margin = 42
    line_height = 14
    usable_width = page_width - (margin * 2)
    title_band_height = 34
    header_line = " | ".join(headers)
    text_lines: list[str] = [header_line, "-" * min(len(header_line), 92)]
    for row in rows or [["Sin registros disponibles"]]:
        row_text = " | ".join(
            f"{headers[index]}: {_truncate_pdf_cell(cell, 42)}" for index, cell in enumerate(row[: len(headers)])
        )
        wrapped = wrap(row_text, width=92) or [" "]
        text_lines.extend(wrapped)
        text_lines.append("")
    lines_per_page = 42
    pages = [text_lines[index : index + lines_per_page] for index in range(0, len(text_lines), lines_per_page)] or [["Sin registros disponibles"]]
    objects: list[bytes] = []
    page_ids: list[int] = []
    font_id = 1
    font_bold_id = 2
    pages_id = 3
    next_id = 4
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    objects.append(b"<< /Type /Pages /Kids [] /Count 0 >>")
    for page_index, page_lines in enumerate(pages, start=1):
        content_lines = [
            "0.12 0.36 0.78 rg",
            f"{margin} {page_height - margin - title_band_height} {usable_width} {title_band_height} re f",
            "0.95 0.97 1 rg",
            f"{margin} {page_height - margin - title_band_height - 26} {usable_width} 22 re f",
            "0.85 0.89 0.94 RG",
            f"{margin} 70 {usable_width} {page_height - 170} re S",
            "BT",
            f"/F2 20 Tf {margin + 12} {page_height - margin - 24} Td ({_pdf_escape(title)}) Tj",
            "ET",
            "BT",
            f"/F1 10 Tf {margin + 12} {page_height - margin - 48} Td ({_pdf_escape(subtitle)}) Tj",
            "ET",
            "BT",
            f"/F1 9 Tf {page_width - margin - 72} {page_height - margin - 48} Td (Pagina {page_index}/{len(pages)}) Tj",
            "ET",
        ]
        cursor_y = page_height - 112
        for line_index, line in enumerate(page_lines):
            if line_index == 0:
                content_lines.extend(["0.16 0.22 0.35 rg", f"{margin + 10} {cursor_y} 0 0 re f", "BT", f"/F2 10 Tf {margin + 10} {cursor_y} Td ({_pdf_escape(line)}) Tj", "ET"])
            else:
                content_lines.extend(["BT", f"/F1 9 Tf {margin + 10} {cursor_y} Td ({_pdf_escape(line)}) Tj", "ET"])
            cursor_y -= line_height
        stream = "\n".join(content_lines).encode("latin-1", errors="replace")
        content_obj = f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream"
        content_id = next_id
        next_id += 1
        page_id = next_id
        next_id += 1
        objects.append(content_obj)
        objects.append(f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {page_width} {page_height}] /Resources << /Font << /F1 {font_id} 0 R /F2 {font_bold_id} 0 R >> >> /Contents {content_id} 0 R >>".encode("latin-1"))
        page_ids.append(page_id)
    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{' '.join(f'{pid} 0 R' for pid in page_ids)}] /Count {len(page_ids)} >>".encode("latin-1")
    catalog_id = next_id
    objects.append(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("latin-1"))
    buffer = BytesIO()
    buffer.write(b"%PDF-1.4\n")
    offsets = [0]
    for object_id, payload in enumerate(objects, start=1):
        offsets.append(buffer.tell())
        buffer.write(f"{object_id} 0 obj\n".encode("latin-1"))
        buffer.write(payload)
        buffer.write(b"\nendobj\n")
    xref_position = buffer.tell()
    buffer.write(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    buffer.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.write(f"{offset:010d} 00000 n \n".encode("latin-1"))
    buffer.write(f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_position}\n%%EOF".encode("latin-1"))
    return buffer.getvalue()
