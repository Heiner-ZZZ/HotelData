from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from .excel_service import render_sheets_to_xlsx
from .pdf_service import render_html_to_pdf
from .schemas import ExcelReportRequest, PdfReportRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("/pdf", response_class=Response)
async def generate_pdf(payload: PdfReportRequest) -> Response:
    """Convert an HTML document to a PDF via WeasyPrint and return the bytes.

    Body:
      - html: full HTML document string (inline <style> blocks supported)
      - filename: base filename (no extension)
      - document_title: optional override that the client can surface in the <title>
    """
    if not payload.html or not payload.html.strip():
        raise HTTPException(status_code=400, detail="El campo 'html' no puede estar vacío.")
    if len(payload.html) > 5_000_000:  # 5 MB safety cap
        raise HTTPException(status_code=413, detail="El HTML excede el tamaño máximo permitido.")

    try:
        pdf_bytes = render_html_to_pdf(payload.html)
    except Exception as exc:  # noqa: BLE001 — surface useful message to caller
        logger.exception("WeasyPrint failed to render PDF: %s", exc)
        raise HTTPException(status_code=500, detail=f"Error al renderizar PDF: {exc}") from exc

    safe_filename = (payload.filename or "reporte").replace('"', "").replace("..", "_").strip() or "reporte"
    headers = {
        "Content-Disposition": f'attachment; filename="{safe_filename}.pdf"',
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@router.post("/xlsx", response_class=Response)
async def generate_xlsx(payload: ExcelReportRequest) -> Response:
    """Build a styled XLSX workbook from structured rows and return the bytes.

    Body:
      - filename: base filename (no extension)
      - sheet_title: optional large title row at the top of every sheet
      - sheets: list of ExcelSheet with headers + rows
    """
    if not payload.sheets:
        raise HTTPException(status_code=400, detail="Debe incluir al menos una hoja.")

    try:
        xlsx_bytes = render_sheets_to_xlsx(payload.sheets, payload.sheet_title)
    except Exception as exc:  # noqa: BLE001
        logger.exception("OpenPyXL failed to render XLSX: %s", exc)
        raise HTTPException(status_code=500, detail=f"Error al generar XLSX: {exc}") from exc

    safe_filename = (payload.filename or "reporte").replace('"', "").replace("..", "_").strip() or "reporte"
    headers = {
        "Content-Disposition": f'attachment; filename="{safe_filename}.xlsx"',
        "X-Content-Type-Options": "nosniff",
    }
    return Response(content=xlsx_bytes, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
