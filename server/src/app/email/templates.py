"""Shared HTML email templates with a clean, modern, square design.

Design principles:
- Square corners (no border-radius)
- Thin 1px borders
- No emoji characters
- Logo image instead of text branding
- Clean white backgrounds
- Subtle gray dividers
"""

from __future__ import annotations

from typing import Any


# ── Config ──

_BODY_CSS = (
    "margin:0;padding:0;background-color:#f3f4f6;"
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif"
)


# ── Helpers ──

def is_localhost_url(url: str) -> bool:
    """Return True if *url* is a localhost/127.0.0.1 address."""
    cleaned = url.strip().lower()
    return (
        "localhost" in cleaned
        or "127.0.0.1" in cleaned
        or "0.0.0.0" in cleaned
    )


def safe_url(url: str | None) -> str | None:
    """Return *url* unchanged if it points to a real domain, else None."""
    if url and not is_localhost_url(url):
        return url
    return None


def logo_img(base_url: str) -> str:
    """Return an <img> tag for the HotelData logo, or empty if localhost."""
    src = f"{base_url.rstrip('/')}/assets/logo-hoteldata.png"
    if is_localhost_url(src):
        return ""
    return (
        f'<img src="{src}" alt="HotelData Hub" width="160" '
        f'style="display:block;max-width:160px;height:auto;border:0">'
    )


# ── Layout components ──

def detail_row(label: str, value: str) -> str:
    """A single row in a details table."""
    return (
        f'<tr>\n'
        f'  <td style="padding:8px 12px;border-bottom:1px solid #e0e3e5;'
        f'color:#6f797d;font-size:13px;vertical-align:top;white-space:nowrap;min-width:100px">'
        f'{label}</td>\n'
        f'  <td style="padding:8px 12px;border-bottom:1px solid #e0e3e5;font-size:13px;color:#191c1e">'
        f'{value}</td>\n'
        f'</tr>'
    )


def detail_table(title: str, rows: str) -> str:
    """A bordered details table with a header row."""
    header = (
        f'<tr>\n'
        f'  <td style="padding:10px 12px;background:#f7f9fb;'
        f'font-size:12px;font-weight:600;color:#3f484c;'
        f'border-bottom:1px solid #e0e3e5;text-transform:uppercase;letter-spacing:0.04em" '
        f'colspan="2">{title}</td>\n'
        f'</tr>'
    )
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0" '
        f'style="border:1px solid #e0e3e5;margin-bottom:20px">\n'
        f'{header}\n{rows}\n'
        f'</table>'
    )


def cta_button(url: str | None, text: str = "Ver detalle") -> str:
    """A centered call-to-action button. Returns empty string if *url* is localhost."""
    final_url = safe_url(url)
    if not final_url:
        # No real URL available — show muted text instead
        return (
            f'<table width="100%" cellpadding="0" cellspacing="0">\n'
            f'  <tr>\n'
            f'    <td align="center" style="padding:4px 0 0;font-size:12px;color:#9ca3af">\n'
            f'      Inicia sesion en HotelData para ver los detalles.\n'
            f'    </td>\n'
            f'  </tr>\n'
            f'</table>'
        )
    return (
        f'<table width="100%" cellpadding="0" cellspacing="0">\n'
        f'  <tr>\n'
        f'    <td align="center">\n'
        f'      <a href="{final_url}" '
        f'style="display:inline-block;padding:10px 24px;background:#006076;color:#fff;'
        f'text-decoration:none;font-size:14px;font-weight:600">{text}</a>\n'
        f'    </td>\n'
        f'  </tr>\n'
        f'</table>'
    )


def status_badge(text: str, bg_color: str = "#f7f9fb", text_color: str = "#3f484c") -> str:
    """A simple text badge (square, no emoji)."""
    return (
        f'<span style="display:inline-block;padding:3px 10px;'
        f'background:{bg_color};color:{text_color};font-size:12px;font-weight:600">'
        f'{text}</span>'
    )


def divider() -> str:
    """Thin horizontal divider."""
    return '<hr style="border:0;border-top:1px solid #e0e3e5;margin:20px 0">'


# ── Base layout ──

def base_layout(
    headline: str,
    body_content: str,
    footer_note: str = "Este es un mensaje automatico de HotelData Hub.",
    logo_url: str = "",
) -> str:
    """Return a complete HTML email page with the HotelData branded layout.

    Parameters
    ----------
    headline : str
        Short headline shown below the logo.
    body_content : str
        HTML body content (tables, paragraphs, etc.).
    footer_note : str
        Small text in the footer area.
    logo_url : str
        Base URL for the logo image. If empty or localhost, logo is hidden.
    """
    # Logo section — show only if a real URL is available
    logo_html = ""
    if logo_url and not is_localhost_url(logo_url):
        logoSrc = f"{logo_url.rstrip('/')}/assets/logo-hoteldata.png"
        logo_html = (
            f'<tr>\n'
            f'  <td align="center" style="padding:0 0 16px">\n'
            f'    <img src="{logoSrc}" alt="HotelData Hub" width="160" '
            f'style="display:block;max-width:160px;height:auto;border:0">\n'
            f'  </td>\n'
            f'</tr>'
        )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="{_BODY_CSS}">
  <table align="center" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:24px auto">
    {logo_html}
    <tr>
      <td style="background:#ffffff;border:1px solid #e0e3e5;padding:32px">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="padding:0 0 16px">
              <h1 style="margin:0;font-size:18px;font-weight:700;color:#191c1e">{headline}</h1>
            </td>
          </tr>
          <tr>
            <td style="font-size:14px;color:#3f484c;line-height:1.6">
              {body_content}
            </td>
          </tr>
        </table>
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td style="padding:20px 0 0">
              <hr style="border:0;border-top:1px solid #e0e3e5;margin:0">
            </td>
          </tr>
          <tr>
            <td style="padding:12px 0 0;font-size:12px;color:#9ca3af;text-align:center;line-height:1.5">
              {footer_note}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
