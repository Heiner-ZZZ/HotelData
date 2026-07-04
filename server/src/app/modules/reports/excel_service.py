from __future__ import annotations

import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .schemas import ExcelSheet


_HEADER_FILL = PatternFill("solid", fgColor="FF1E3C78")  # deep navy
_HEADER_FONT = Font(bold=True, color="FFFFFFFF", size=11, name="DejaVu Sans")
_TOTAL_FILL = PatternFill("solid", fgColor="FFE8F5E9")  # pale green
_NORMAL_FONT = Font(size=10, name="DejaVu Sans")
_ALT_FILL = PatternFill("solid", fgColor="FFF8F9FC")  # off-white


def _cell_style(cell, raw: dict) -> None:
    """Apply a single cell's style overrides from raw dict."""
    if raw.get("bold") or raw.get("italic"):
        cell.font = Font(
            bold=raw.get("bold", False),
            italic=raw.get("italic", False),
            color=raw.get("font_color", "FF1F2937").replace("#", ""),
            size=10,
            name="DejaVu Sans",
        )
    if raw.get("fill_color"):
        cell.fill = PatternFill("solid", fgColor=raw["fill_color"].replace("#", "").upper())
    if raw.get("font_color") and not (raw.get("bold") or raw.get("italic")):
        cell.font = Font(
            color=raw["font_color"].replace("#", ""),
            size=10,
            name="DejaVu Sans",
        )
    if raw.get("number_format"):
        cell.number_format = raw["number_format"]
    if raw.get("align"):
        cell.alignment = Alignment(horizontal=raw["align"], vertical="center", wrap_text=True)


def render_sheets_to_xlsx(sheets: list[ExcelSheet], sheet_title: str | None = None) -> bytes:
    """Build a styled workbook from structured sheets data using OpenPyXL.

    Each sheet writes:
      - Title row (sheet.sheet_title if provided)
      - Header row with deep-navy background and white bold text
      - Alternating row fills (every even row)
      - Frozen header so it's always visible while scrolling
      - Column widths from sheet.column_widths (colLetter -> width in chars)
    """
    workbook = Workbook()
    workbook.remove(workbook.active)  # we'll add sheets explicitly

    for idx, sheet in enumerate(sheets):
        ws = workbook.create_sheet(title=sheet.name[:31])

        start_row = 1
        if sheet_title:
            ws.cell(row=1, column=1, value=sheet_title)
            ws.cell(row=1, column=1).font = Font(bold=True, size=14, color="FF1E3C78", name="DejaVu Sans")
            ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(1, len(sheet.headers)))
            start_row = 2

        # Header row
        for col_idx, header in enumerate(sheet.headers, start=1):
            cell = ws.cell(row=start_row, column=col_idx, value=header.label if hasattr(header, "label") else str(header))
            cell.fill = _HEADER_FILL
            cell.font = _HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            if header.bold or header.fill_color or header.font_color:
                _cell_style(cell, header.dict())

        # Body rows
        for r_idx, row in enumerate(sheet.rows):
            excel_row = start_row + 1 + r_idx
            for c_idx, cell_value in enumerate(row, start=1):
                cell = ws.cell(row=excel_row, column=c_idx, value=cell_value)
                cell.font = _NORMAL_FONT
                cell.alignment = Alignment(vertical="center", wrap_text=True)
                if r_idx % 2 == 0:
                    cell.fill = _ALT_FILL
                # Detect currency / numbers and format them
                if isinstance(cell_value, (int, float)) and not isinstance(cell_value, bool):
                    cell.number_format = '"$"#,##0.00;[Red]"-$"#,##0.00'
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                elif isinstance(cell_value, str) and cell_value.startswith("$"):
                    cell.alignment = Alignment(horizontal="right", vertical="center")

        # Column widths
        if sheet.column_widths:
            for col_letter, width in sheet.column_widths.items():
                ws.column_dimensions[col_letter].width = max(8, float(width))
        else:
            for col_idx in range(1, len(sheet.headers) + 1):
                ws.column_dimensions[get_column_letter(col_idx)].width = 18

        # Row heights
        ws.row_dimensions[start_row].height = 24
        for r in range(start_row + 1, start_row + 1 + len(sheet.rows)):
            ws.row_dimensions[r].height = 18

        # Freeze header
        if sheet.freeze_header:
            ws.freeze_panes = ws.cell(row=start_row + 1, column=1)

        # Auto-filter on header
        ws.auto_filter.ref = (
            f"{get_column_letter(1)}{start_row}:{get_column_letter(len(sheet.headers))}{start_row}"
        )

        # Print setup — landscape, fit to width
        ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_title_rows = f"{start_row}:{start_row}"
        ws.page_margins.left = 0.4
        ws.page_margins.right = 0.4
        ws.page_margins.top = 0.5
        ws.page_margins.bottom = 0.5

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer.read()
