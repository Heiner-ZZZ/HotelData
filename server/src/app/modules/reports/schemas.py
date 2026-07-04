from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PdfReportRequest(BaseModel):
    """Request body for POST /api/reports/pdf."""

    html: str = Field(..., description="Complete HTML document (with <style> tags)")
    filename: str = Field(..., description="Base filename without extension (e.g. 'estado_resultados')")
    document_title: str | None = Field(None, description="Optional override for <title> and @page header")


class ExcelCellStyle(BaseModel):
    """Optional per-cell style override applied by OpenPyXL."""

    bold: bool = False
    italic: bool = False
    fill_color: str | None = None  # hex like 'FF166534'
    font_color: str | None = None  # hex like 'FFFFFFFF'
    number_format: str | None = None  # e.g. '"$"#,##0.00'
    align: str | None = None  # 'left' | 'center' | 'right'


class ExcelHeaderCell(ExcelCellStyle):
    label: str


class ExcelRowCell(ExcelCellStyle):
    """A cell value. ``value`` can be str, int, float, bool, or None."""

    value: Any = None


class ExcelRow:
    """Just a list of cells — defined inline in the parent module."""

    pass


class ExcelSheet(BaseModel):
    name: str
    headers: list[ExcelHeaderCell]
    rows: list[list[Any]]  # raw values per cell
    column_widths: dict[str, float] | None = None  # colLetter -> width
    freeze_header: bool = True


class ExcelReportRequest(BaseModel):
    """Request body for POST /api/reports/xlsx."""

    filename: str = Field(..., description="Base filename without extension")
    sheet_title: str | None = None
    sheets: list[ExcelSheet]
