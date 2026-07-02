"""Email HTML templates for reservation notifications.

All template functions are pure — they receive pre-formatted values
and return complete HTML strings. Uses the shared layout from
``src.app.email.templates`` for consistent branding.
"""

from __future__ import annotations

from src.app.email.templates import (
    base_layout,
    cta_button,
    detail_row,
    detail_table,
    status_badge,
)


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
    """Email HTML for notifying staff about a new booking.

    Uses ``{{STAFF_NAME}}`` as a placeholder — the caller must
    ``.replace("{{STAFF_NAME}}", actual_name)`` per recipient.
    """
    rows = detail_table(
        "Detalles de la reserva",
        detail_row("ID", f"<strong>{booking_id}</strong>")
        + detail_row("Hotel", hotel_label)
        + detail_row("Huesped", f"{guest_name}<br><span style=\"color:#6f797d;font-size:12px\">{guest_email}</span>")
        + detail_row("Check-in", check_in_date)
        + detail_row("Check-out", check_out_date)
        + detail_row("Estancia", nights_label)
        + detail_row("Ocupacion", guests_label)
        + detail_row("Total", price_line)
        + comment_section
        + detail_row(
            "Estado",
            status_badge("PENDIENTE", bg_color="#fef3c7", text_color="#92400e"),
        ),
    )

    body = (
        f'<p style="margin:0 0 20px;font-size:14px;color:#3f484c">'
        f'Hola <strong>{{STAFF_NAME}}</strong>,</p>\n'
        f'<p style="margin:0 0 20px;font-size:13px;color:#6f797d;line-height:1.5">\n'
        f'  Se ha recibido una <strong>nueva solicitud de reserva</strong> para tu propiedad.\n'
        f'  Revisa los detalles y confirma o rechaza desde el panel de gestion.\n'
        f'</p>\n'
        f'{rows}'
        f'{cta_button(detail_url, "Ver reserva en HotelData")}'
    )

    return base_layout(
        "Nueva solicitud de reserva",
        body,
        footer_note=(
            "Este es un mensaje automatico de HotelData Hub.<br>"
            "Puedes gestionar esta y otras reservas desde tu panel de administracion."
        ),
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
    """Email HTML for notifying staff about a guest check-in or check-out.

    Uses ``{{STAFF_NAME}}`` as a placeholder — the caller must
    ``.replace("{{STAFF_NAME}}", actual_name)`` per recipient.
    """
    is_check_in = event_type == "check_in"
    badge_color = "#dbeafe" if is_check_in else "#f0fdf4"
    badge_text_color = "#1e40af" if is_check_in else "#166534"
    badge_text = "CHECK-IN" if is_check_in else "CHECK-OUT"
    action_label = "check-in" if is_check_in else "check-out"
    action_title = "Check-in completado" if is_check_in else "Check-out completado"

    rows = detail_table(
        "Detalles del huesped",
        detail_row("ID", f'<span style="font-family:monospace">{booking_id}</span>')
        + detail_row("Hotel", hotel_label)
        + detail_row("Huesped", guest_name)
        + detail_row("Check-in", check_in_date)
        + detail_row("Check-out", check_out_date)
        + detail_row("Estancia", nights_label)
        + detail_row(
            "Evento",
            status_badge(badge_text, bg_color=badge_color, text_color=badge_text_color),
        ),
    )

    body = (
        f'<p style="margin:0 0 20px;font-size:14px;color:#3f484c">'
        f'Hola <strong>{{STAFF_NAME}}</strong>,</p>\n'
        f'<p style="margin:0 0 20px;font-size:13px;color:#6f797d;line-height:1.5">\n'
        f'  El huesped <strong>{guest_name}</strong> ha completado el <strong>{action_label}</strong>.\n'
        f'  Puedes ver los detalles actualizados desde el panel de gestion.\n'
        f'</p>\n'
        f'{rows}'
        f'{cta_button(detail_url, "Ver reserva en HotelData")}'
    )

    return base_layout(
        action_title,
        body,
        footer_note=(
            "Este es un mensaje automatico de HotelData Hub.<br>"
            "El estado de la reserva se actualiza en tiempo real en tu panel."
        ),
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
    """Email HTML for notifying a guest about a status change (confirmed/rejected/cancelled)."""
    rows = detail_table(
        "Resumen de tu reserva",
        detail_row("ID", f'<span style="font-family:monospace">{booking_id}</span>')
        + detail_row("Hotel", hotel_label)
        + detail_row("Check-in", check_in_date)
        + detail_row("Check-out", check_out_date)
        + detail_row("Estancia", nights_label)
        + detail_row("Total", price_line)
        + detail_row("Estado", badge_html),
    )

    body = (
        f'<p style="margin:0 0 12px;font-size:14px;color:#3f484c">'
        f'Hola <strong>{guest_name}</strong>,</p>\n'
        f'<p style="margin:0 0 20px;font-size:13px;color:#6f797d;line-height:1.5">'
        f'{body_intro}</p>\n'
        f'{rows}'
        f'{cta_button(detail_url)}'
    )

    return base_layout(headline, body)


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
    rows = detail_table(
        "Factura",
        detail_row("No. Factura", f"<strong>{invoice_number}</strong>")
        + detail_row("Total", invoice_total)
        + detail_row("Check-in", check_in_date)
        + detail_row("Check-out", check_out_date)
        + detail_row("Estancia", nights_label)
        + detail_row(
            "Estado",
            status_badge("EMITIDA", bg_color="#dbeafe", text_color="#1e40af"),
        ),
    )

    body = (
        f'<p style="margin:0 0 12px;font-size:14px;color:#3f484c">'
        f'Hola <strong>{guest_name}</strong>,</p>\n'
        f'<p style="margin:0 0 20px;font-size:13px;color:#6f797d;line-height:1.5">\n'
        f'  Tu estancia en <strong>{hotel_label}</strong> ha finalizado. Tu factura '
        f'<strong>{invoice_number}</strong> por <strong>{invoice_total}</strong> ya esta disponible.\n'
        f'</p>\n'
        f'{rows}'
        f'{cta_button(invoice_url, "Ver mi factura")}'
    )

    return base_layout(
        "Gracias por tu visita",
        body,
        footer_note=(
            "Este es un mensaje automatico de HotelData Hub.<br>"
            "Puedes descargar tu factura desde tu panel de huesped."
        ),
    )
