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
        f'<img src="{src}" alt="HotelData" width="160" '
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
            '<table width="100%" cellpadding="0" cellspacing="0">\n'
            '  <tr>\n'
            '    <td align="center" style="padding:4px 0 0;font-size:12px;color:#9ca3af">\n'
            '      Inicia sesion en HotelData para ver los detalles.\n'
            '    </td>\n'
            '  </tr>\n'
            '</table>'
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
    footer_note: str = "Este es un mensaje automatico de HotelData.",
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
            '<tr>\n'
            '  <td align="center" style="padding:0 0 16px">\n'
            f'    <img src="{logoSrc}" alt="HotelData" width="160" '
            'style="display:block;max-width:160px;height:auto;border:0">\n'
            '  </td>\n'
            '</tr>'
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


# ─────────────────────────────────────────────────────────────────
# Property-owner onboarding email
# ─────────────────────────────────────────────────────────────────


def onboarding_property_verification(
    email: str,
    display_name: str,
    code: str,
    base_url: str = "",
    expiry_minutes: int = 15,
) -> str:
    """Return the FULL HTML document for the property-owner onboarding
    verification code email.

    Subject (set by the caller via `send_email`): 'Tu código de
    activación — HotelData'.

    Distinct copy from the regular user-registration verification
    email: this one frames the recipient as a future hotel host, lists
    what their management panel will unlock once they confirm, and uses
    a different headline ('Activa tu panel de gestión') so they don't
    confuse the two flows mid-onboarding.
    """
    # Square digit boxes (consistent visual style with `_send_verification_code`).
    digits_html = ""
    for i, digit in enumerate(code):
        margin_left = "margin-left:6px;" if i > 0 else ""
        digits_html += (
            f'<td style="width:44px;height:52px;text-align:center;'
            f'font-size:26px;font-weight:700;font-family:monospace;'
            f'color:#191c1e;background:#f7f9fb;border:1px solid #d0d5d8;'
            f'{margin_left}">'
            f'{digit}'
            f'</td>'
        )

    body_content = (
        f'<p style="margin:0 0 16px;font-size:14px;color:#3f484c">'
        f'Hola <strong>{display_name}</strong>,</p>\n'
        f'<p style="margin:0 0 14px;font-size:13px;color:#6f797d;line-height:1.5">\n'
        f'  Estás a un paso de activar tu panel de gestión en HotelData. '
        f'Usa el siguiente código para confirmar el alta de tu alojamiento '
        f'y acceder inmediatamente a:\n'
        f'</p>\n'
        f'<ul style="margin:0 0 20px;padding-left:20px;font-size:13px;color:#3f484c;line-height:1.6">\n'
        f'  <li>Gestión de disponibilidad y tarifas</li>\n'
        f'  <li>Reservas y huéspedes en tiempo real</li>\n'
        f'  <li>Reportes de revenue y operación</li>\n'
        f'</ul>\n'
        f'<table align="center" cellpadding="0" cellspacing="0" style="margin:0 auto 20px">\n'
        f'  <tr>{digits_html}</tr>\n'
        f'</table>\n'
        f'<p style="margin:0;font-size:13px;color:#6f797d;line-height:1.5">'
        f'Este código expira en <strong>{expiry_minutes} minutos</strong>.<br>'
        f'Si no solicitaste este registro, ignora este mensaje.'
        f'</p>'
    )

    return base_layout(
        headline="Activa tu panel de gestión",
        body_content=body_content,
        footer_note=(
            "Este es un mensaje automático de HotelData.<br>"
            "Si no solicitaste este registro, ignora este mensaje."
        ),
        logo_url=base_url,
    )


# ─────────────────────────────────────────────────────────────────
# Hotel-approval emails (UX-2 — docs/EXPERIENCIA_DUENO_PENDIENTE.md §4)
# ─────────────────────────────────────────────────────────────────


def registration_approved(
    hotel_name: str,
    plan_label: str,
    monthly_usd: float,
    base_url: str = "",
    due_date=None,
    payment_methods=None,
) -> str:
    """Full HTML for the owner-approval email.

    Subject (set by the caller): 'Tu alojamiento fue aprobado — HotelData'.
    When ``due_date`` is present, a "Primera factura" block is appended with
    the payment due date and the manual payment methods (no gateway).
    """
    payment_block = ""
    if due_date is not None:
        rows = detail_row("Vence", due_date.strftime("%d %b %Y"))
        methods = payment_methods or []
        if methods:
            rows += detail_row("Cómo pagar", ", ".join(str(m) for m in methods))
        payment_block = detail_table("Primera factura", rows)

    body_content = (
        f'<p style="margin:0 0 16px;font-size:14px;color:#3f484c">'
        f'¡Buenas noticias!</p>\n'
        f'<p style="margin:0 0 20px;font-size:13px;color:#6f797d;line-height:1.5">\n'
        f'  El alojamiento <strong>{hotel_name}</strong> fue aprobado. Ya puedes '
        f'iniciar sesión y gestionar tu hotel desde el panel de HotelData.\n'
        f'</p>\n'
        f'{detail_table("Plan asignado", detail_row("Plan", plan_label) + detail_row("Mensualidad", f"${monthly_usd:,.0f} USD"))}\n'
        f'{payment_block}'
        f'<p style="margin:0 0 16px;font-size:13px;color:#6f797d;line-height:1.5">'
        f'Accedes como gerente del hotel con todos los permisos de administración.'
        f'</p>\n'
        f'{cta_button(f"{base_url.rstrip('/')}/login", "Ir a mi panel")}'
    )
    return base_layout(
        headline="¡Tu alojamiento fue aprobado!",
        body_content=body_content,
        footer_note="El precio final puede ser ajustado por el administrador al aprobar.",
        logo_url=base_url,
    )


def registration_rejected(
    hotel_name: str,
    reason: str,
    base_url: str = "",
) -> str:
    """Full HTML for the owner-rejection email.

    Subject (set by the caller): 'Tu registro de alojamiento no fue aprobado —
    HotelData'. The admin's reason is never generic — always rendered.
    """
    reason_box = (
        f'<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 20px">\n'
        f'  <tr><td style="padding:14px 16px;border:1px solid #e0e3e5;background:#fbf7f5;'
        f'font-size:13px;color:#8a4b2d;line-height:1.5">{reason}</td></tr>\n'
        f'</table>'
    )
    body_content = (
        f'<p style="margin:0 0 16px;font-size:14px;color:#3f484c">'
        f'Hola,</p>\n'
        f'<p style="margin:0 0 16px;font-size:13px;color:#6f797d;line-height:1.5">\n'
        f'  El alojamiento <strong>{hotel_name}</strong> no fue aprobado. '
        f'Motivo del administrador:\n'
        f'</p>\n'
        f'{reason_box}\n'
        f'<p style="margin:0;font-size:13px;color:#6f797d;line-height:1.5">'
        f'Puedes volver a intentarlo con un nuevo registro en cualquier momento.'
        f'</p>'
    )
    return base_layout(
        headline="Actualización sobre tu registro",
        body_content=body_content,
        footer_note="Este es un mensaje automático de HotelData.",
        logo_url=base_url,
    )


def registration_changes_requested(
    hotel_name: str,
    feedback: str,
    base_url: str = "",
) -> str:
    """Full HTML for the 'changes requested' email.

    Subject (set by the caller): 'Revisa tu registro de alojamiento —
    HotelData'. Links to the edit screen of the pending-owner experience.
    """
    feedback_box = (
        f'<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 20px">\n'
        f'  <tr><td style="padding:14px 16px;border:1px solid #e0e3e5;background:#fbf8ef;'
        f'font-size:13px;color:#6b5418;line-height:1.5">{feedback}</td></tr>\n'
        f'</table>'
    )
    body_content = (
        f'<p style="margin:0 0 16px;font-size:14px;color:#3f484c">'
        f'Hola,</p>\n'
        f'<p style="margin:0 0 16px;font-size:13px;color:#6f797d;line-height:1.5">\n'
        f'  Para aprobar tu alojamiento <strong>{hotel_name}</strong> necesitamos '
        f'ajustar los siguientes datos:\n'
        f'</p>\n'
        f'{feedback_box}\n'
        f'<p style="margin:0 0 20px;font-size:13px;color:#6f797d;line-height:1.5">'
        f'Edita tu registro y vuelve a enviarlo; lo revisaremos de nuevo.'
        f'</p>\n'
        f'{cta_button(f"{base_url.rstrip('/')}/alojamiento-en-revision", "Editar mi registro")}'
    )
    return base_layout(
        headline="Revisa tu registro",
        body_content=body_content,
        footer_note="Este es un mensaje automático de HotelData.",
        logo_url=base_url,
    )


# ─────────────────────────────────────────────────────────────────
# Subscription notifications (PLAN_SUSCRIPCION_Y_PAGOS.md §8)
# ─────────────────────────────────────────────────────────────────


def subscription_payment_received(
    hotel_name: str,
    amount: float,
    reference: str = "",
    base_url: str = "",
) -> str:
    """Full HTML for the owner after declaring a payment (pay).

    Subject (set by the caller): 'Recibimos tu comprobante de pago —
    HotelData'. The money never moves through the system — a human verifies it.
    """
    rows = detail_row("Hotel", hotel_name) + detail_row("Monto declarado", f"${amount:,.2f} USD")
    if reference:
        rows += detail_row("Referencia", reference)
    body_content = (
        f'<p style="margin:0 0 16px;font-size:14px;color:#3f484c">'
        f'Hola,</p>\n'
        f'<p style="margin:0 0 20px;font-size:13px;color:#6f797d;line-height:1.5">\n'
        f'  Recibimos tu comprobante de pago para <strong>{hotel_name}</strong>. '
        f'Lo verificaremos en un plazo máximo de 24 horas hábiles.\n'
        f'</p>\n'
        f'{detail_table("Pago declarado", rows)}\n'
        f'{cta_button(f"{base_url.rstrip('/')}/management/subscription", "Ver mi suscripción")}'
    )
    return base_layout(
        headline="Comprobante recibido",
        body_content=body_content,
        footer_note="Este es un mensaje automático de HotelData.",
        logo_url=base_url,
    )


def subscription_payment_verified(
    hotel_name: str,
    base_url: str = "",
) -> str:
    """Full HTML for the owner when an admin verifies the payment.

    Subject (set by the caller): 'Tu pago fue conciliado — HotelData'.
    """
    body_content = (
        f'<p style="margin:0 0 16px;font-size:14px;color:#3f484c">'
        f'Hola,</p>\n'
        f'<p style="margin:0 0 20px;font-size:13px;color:#6f797d;line-height:1.5">\n'
        f'  Tu pago fue conciliado. La suscripción de <strong>{hotel_name}</strong> '
        f'está activa y tu hotel continúa operando con normalidad.\n'
        f'</p>\n'
        f'{cta_button(f"{base_url.rstrip('/')}/management/subscription", "Ver mi suscripción")}'
    )
    return base_layout(
        headline="Pago conciliado",
        body_content=body_content,
        footer_note="Este es un mensaje automático de HotelData.",
        logo_url=base_url,
    )


def subscription_payment_rejected(
    hotel_name: str,
    reason: str,
    base_url: str = "",
) -> str:
    """Full HTML for the owner when an admin rejects the proof.

    The admin's reason is never generic — always rendered. Subject (set by the
    caller): 'Tu comprobante fue rechazado — HotelData'.
    """
    reason_box = (
        f'<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 20px">\n'
        f'  <tr><td style="padding:14px 16px;border:1px solid #e0e3e5;background:#fbf7f5;'
        f'font-size:13px;color:#8a4b2d;line-height:1.5">{reason}</td></tr>\n'
        f'</table>'
    )
    body_content = (
        f'<p style="margin:0 0 16px;font-size:14px;color:#3f484c">'
        f'Hola,</p>\n'
        f'<p style="margin:0 0 16px;font-size:13px;color:#6f797d;line-height:1.5">\n'
        f'  No pudimos conciliar el comprobante de <strong>{hotel_name}</strong>. '
        f'Motivo:\n'
        f'</p>\n'
        f'{reason_box}\n'
        f'<p style="margin:0 0 20px;font-size:13px;color:#6f797d;line-height:1.5">'
        f'Vuelve a declarar el pago con la referencia correcta para reactivar tu '
        f'suscripción.'
        f'</p>\n'
        f'{cta_button(f"{base_url.rstrip('/')}/management/subscription", "Subir comprobante")}'
    )
    return base_layout(
        headline="Comprobante rechazado",
        body_content=body_content,
        footer_note="Este es un mensaje automático de HotelData.",
        logo_url=base_url,
    )


def subscription_overdue(
    hotel_name: str,
    amount: float,
    due_date=None,
    base_url: str = "",
) -> str:
    """Full HTML for the owner when a subscription invoice is overdue.

    Subject (set by the caller): 'Tu factura de suscripción venció — HotelData'.
    """
    rows = detail_row("Hotel", hotel_name) + detail_row("Monto vencido", f"${amount:,.2f} USD")
    if due_date is not None:
        rows += detail_row("Venció el", due_date.strftime("%d %b %Y"))
    body_content = (
        f'<p style="margin:0 0 16px;font-size:14px;color:#3f484c">'
        f'Hola,</p>\n'
        f'<p style="margin:0 0 20px;font-size:13px;color:#6f797d;line-height:1.5">\n'
        f'  La factura de <strong>{hotel_name}</strong> venció sin pago. '
        f'Regulariza el pago para evitar la suspensión operativa del hotel.\n'
        f'</p>\n'
        f'{detail_table("Factura vencida", rows)}\n'
        f'{cta_button(f"{base_url.rstrip('/')}/management/subscription", "Regularizar pago")}'
    )
    return base_layout(
        headline="Factura de suscripción vencida",
        body_content=body_content,
        footer_note="Este es un mensaje automático de HotelData.",
        logo_url=base_url,
    )


def subscription_suspended(
    hotel_name: str,
    amount: float,
    base_url: str = "",
) -> str:
    """Full HTML for the owner when the hotel is suspended for non-payment.

    Subject (set by the caller): 'Tu hotel fue suspendido por impago —
    HotelData'.
    """
    body_content = (
        f'<p style="margin:0 0 16px;font-size:14px;color:#3f484c">'
        f'Hola,</p>\n'
        f'<p style="margin:0 0 20px;font-size:13px;color:#6f797d;line-height:1.5">\n'
        f'  El hotel <strong>{hotel_name}</strong> quedó suspendido por impago '
        f'(adeudo de <strong>${amount:,.2f} USD</strong>). Está fuera de operaciones '
        f'hasta que regularices el pago.\n'
        f'</p>\n'
        f'<p style="margin:0 0 20px;font-size:13px;color:#6f797d;line-height:1.5">'
        f'Regulariza tu pago y quedará reactivado de inmediato tras la conciliación.'
        f'</p>\n'
        f'{cta_button(f"{base_url.rstrip('/')}/management/subscription", "Regularizar pago")}'
    )
    return base_layout(
        headline="Hotel suspendido por impago",
        body_content=body_content,
        footer_note="Este es un mensaje automático de HotelData.",
        logo_url=base_url,
    )
