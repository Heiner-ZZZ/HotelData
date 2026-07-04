from __future__ import annotations

from weasyprint import HTML, default_url_fetcher


def _safe_url_fetcher(url: str):
    """Reject local file:// URIs and non-http(s) protocols to prevent SSRF
    and unintended embedding of server-side resources into the PDF.
    Only http: and https: are allowed; data: URIs are allowed for inline
    base64 images.
    """
    if url.startswith("file://"):
        return None
    if url.startswith(("http://", "https://", "data:")):
        return default_url_fetcher(url)
    return None


def render_html_to_pdf(html: str) -> bytes:
    """Render an HTML string to PDF bytes using WeasyPrint.

    Returns the PDF as bytes (caller is responsible for streaming/returning
    the bytes to the client).
    """
    pdf_bytes = HTML(string=html, url_fetcher=_safe_url_fetcher).write_pdf()
    return pdf_bytes
