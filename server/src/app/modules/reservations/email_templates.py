"""Email HTML templates for reservation notifications.

All template functions are pure — they receive pre-formatted values
and return complete HTML strings. No database access, no side effects.
"""

from __future__ import annotations

from typing import Any


# ═══════════════════════════════════════════════════════════════════════
# Shared layout helpers
# ═══════════════════════════════════════════════════════════════════════

_BASE_CSS = (
    "margin:0;padding:0;background-color:#f3f4f6;"
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif"
)


def _detail_row(label: str, value: str) -> str:
    return f"""<tr>
    <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;color:#4b5563;font-size:14px;vertical-align:top;white-space:nowrap">{label}</td>
    <td style="padding:8px 12px;border-bottom:1px solid #e5e7eb;font-size:14px">{value}</td>
  </tr>"""


def _detail_table(title: str, rows: str) -> str:
    return f"""<table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;margin-bottom:20px">
  <tr><td style="background:#f9fafb;padding:10px 14px;font-size:13px;font-weight:600;color:#374151;border-bottom:1px solid #e5e7eb" colspan="2">{title}</td></tr>
  {rows}
</table>"""


def _cta_button(url: str, text: str = "Ver detalle en HotelData →") -> str:
    return f"""<table width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td align="center">
      <a href="{url}" style="display:inline-block;padding:12px 28px;background:#1463ff;color:#fff;text-decoration:none;border-radius:10px;font-size:15px;font-weight:600">{text}</a>
    </td>
  </tr>
</table>"""


def _base_layout(
    headline: str,
    body_content: str,
    footer_note: str = "Este es un mensaje automático de HotelData Hub.",
) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="{_BASE_CSS}">
  <table align="center" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;margin:32px auto">
    <tr>
      <td style="background:linear-gradient(135deg,#1463ff,#0a3d9e);border-radius:16px 16px 0 0;padding:24px 32px;text-align:center">
        <h1 style="margin:0;color:#fff;font-size:20px;font-weight:700">🏨 HotelData</h1>
        <p style="margin:4px 0 0;color:rgba(255,255,255,0.8);font-size:14px">{headline}</p>
      </td>
    </tr>
    <tr>
      <td style="background:#fff;padding:32px;border-radius:0 0 16px 16px;box-shadow:0 4px 12px rgba(0,0,0,0.06)">
        {body_content}
        <p style="margin:16px 0 0;font-size:12px;color:#9ca3af;text-align:center;line-height:1.4">
          {footer_note}<br>
          Si tienes dudas, contacta al hotel directamente.
        </p>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════════════
# Public template functions
# ═══════════════════════════════════════════════════════════════════════

def staff_new_booking_html(
    hotel_label: str,
    booking_id: str,
    guest_name: str,
    guest_email: str,
    check_in_date: str,
    check_out_date: str,
    nights_label: str,
    guests_label: str,
    price_line: str,
    comment_section: str,
    detail_url: str,
) -> str:
    """Full email HTML for notifying staff about a new booking.

    Uses ``{{STAFF_NAME}}`` as a placeholder — the caller must
    ``.replace("{{STAFF_NAME}}", actual_name)`` per recipient.
    """
    rows = _detail_table(
        "📋 Detalles de la reserva",
        _detail_row("ID", f"<strong>{booking_id}</strong>")
        + _detail_row("Hotel", hotel_label)
        + _detail_row("Huésped", f"{guest_name}<br><span style=\"color:#6b7280;font-size:12px\">{guest_email}</span>")
        + _detail_row("Check-in", check_in_date)
        + _detail_row("Check-out", check_out_date)
        + _detail_row("Estancia", nights_label)
        + _detail_row("Ocupación", guests_label)
        + _detail_row("Total", price_line)
        + comment_section
        + _detail_row(
            "Estado",
            "<span style=\"display:inline-block;padding:2px 10px;border-radius:12px;"
            "background:#fef3c7;color:#92400e;font-size:12px;font-weight:600\">PENDIENTE</span>",
        ),
    )

    body = f"""<p style="margin:0 0 20px;font-size:15px;color:#374151">Hola <strong>{{{{STAFF_NAME}}}}</strong>,</p>
<p style="margin:0 0 20px;font-size:14px;color:#4b5563;line-height:1.5">
  Se ha recibido una <strong style="color:#1463ff">nueva solicitud de reserva</strong> para tu propiedad.
  Revisa los detalles y confirma o rechaza desde el panel de gestión.
</p>
{rows}
{_cta_button(detail_url, "Ver reserva en HotelData →")}"""

    return _base_layout(
        "Nueva solicitud de reserva",
        body,
        footer_note="Este es un mensaje automático de HotelData Hub.<br>Puedes gestionar esta y otras reservas desde tu panel de administración.",
    )


def staff_check_event_html(
    event_type: str,  # "check_in" or "check_out"
    hotel_label: str,
    booking_id: str,
    guest_name: str,
    check_in_date: str,
    check_out_date: str,
    nights_label: str,
    detail_url: str,
) -> str:
    """Full email HTML for notifying staff about a guest check-in or check-out.

    Uses ``{{STAFF_NAME}}`` as a placeholder — the caller must
    ``.replace("{{STAFF_NAME}}", actual_name)`` per recipient.
    """
    is_check_in = event_type == "check_in"
    badge_color = "#dbeafe;color:#1e40af" if is_check_in else "#f0fdf4;color:#166534"
    badge_icon = "🔑" if is_check_in else "👋"
    badge_text = "CHECK-IN" if is_check_in else "CHECK-OUT"
    action_label = "check-in" if is_check_in else "check-out"
    action_title = "Check-in completado" if is_check_in else "Check-out completado"

    rows = _detail_table(
        "📋 Detalles del huésped",
        _detail_row("ID", f"<span style=\"font-family:monospace\">{booking_id}</span>")
        + _detail_row("Hotel", hotel_label)
        + _detail_row("Huésped", guest_name)
        + _detail_row("Check-in", check_in_date)
        + _detail_row("Check-out", check_out_date)
        + _detail_row("Estancia", nights_label)
        + _detail_row(
            "Evento",
            f"<span style=\"display:inline-block;padding:2px 10px;border-radius:12px;"
            f"background:{badge_color};font-size:12px;font-weight:600\">{badge_icon} {badge_text}</span>",
        ),
    )

    body = f"""<p style="margin:0 0 20px;font-size:15px;color:#374151">Hola <strong>{{{{STAFF_NAME}}}}</strong>,</p>
<p style="margin:0 0 20px;font-size:14px;color:#4b5563;line-height:1.5">
  El huésped <strong>{guest_name}</strong> ha completado el <strong>{action_label}</strong>.
  Puedes ver los detalles actualizados desde el panel de gestión.
</p>
{rows}
{_cta_button(detail_url, "Ver reserva en HotelData →")}"""

    return _base_layout(
        action_title,
        body,
        footer_note="Este es un mensaje automático de HotelData Hub.<br>El estado de la reserva se actualiza en tiempo real en tu panel.",
    )


def guest_status_change_html(
    hotel_label: str,
    booking_id: str,
    guest_name: str,
    check_in_date: str,
    check_out_date: str,
    nights_label: str,
    price_line: str,
    badge_html: str,
    headline: str,
    body_intro: str,
    detail_url: str,
) -> str:
    """Full email HTML for notifying a guest about a status change (confirmed/rejected/cancelled)."""
    rows = _detail_table(
        "📋 Resumen de tu reserva",
        _detail_row("ID", f"<span style=\"font-family:monospace\">{booking_id}</span>")
        + _detail_row("Hotel", hotel_label)
        + _detail_row("Check-in", check_in_date)
        + _detail_row("Check-out", check_out_date)
        + _detail_row("Estancia", nights_label)
        + _detail_row("Total", price_line)
        + _detail_row("Estado", badge_html),
    )

    body = f"""<p style="margin:0 0 12px;font-size:15px;color:#374151">Hola <strong>{guest_name}</strong>,</p>
<p style="margin:0 0 20px;font-size:14px;color:#4b5563;line-height:1.5">{body_intro}</p>
{rows}
{_cta_button(detail_url)}"""

    return _base_layout(headline, body)


def guest_invoice_html(
    hotel_label: str,
    booking_id: str,
    guest_name: str,
    check_in_date: str,
    check_out_date: str,
    nights_label: str,
    invoice_number: str,
    invoice_total: str,
    invoice_url: str,
) -> str:
    """Email HTML notifying a guest about an invoice issued post-check-out."""
    rows = _detail_table(
        "📋 Factura",
        _detail_row("No. Factura", f"<strong>{invoice_number}</strong>")
        + _detail_row("Total", invoice_total)
        + _detail_row("Check-in", check_in_date)
        + _detail_row("Check-out", check_out_date)
        + _detail_row("Estancia", nights_label)
        + _detail_row(
            "Estado",
            "<span style=\"display:inline-block;padding:2px 10px;border-radius:12px;"
            "background:#dbeafe;color:#1e40af;font-size:12px;font-weight:600\">EMITIDA</span>",
        ),
    )

    body = f"""<p style="margin:0 0 12px;font-size:15px;color:#374151">Hola <strong>{guest_name}</strong>,</p>
<p style="margin:0 0 20px;font-size:14px;color:#4b5563;line-height:1.5">
  Tu estancia en <strong>{hotel_label}</strong> ha finalizado. Tu factura <strong>{invoice_number}</strong>
  por <strong>{invoice_total}</strong> ya está disponible.
</p>
{rows}
{_cta_button(invoice_url, "Ver mi factura →")}"""

    return _base_layout(
        "¡Gracias por tu visita!",
        body,
        footer_note="Este es un mensaje automático de HotelData Hub.<br>Puedes descargar tu factura desde tu panel de huésped.",
    )
