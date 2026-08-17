"""Máquina de estados de suscripciones (docs/PLAN_SUSCRIPCION_Y_PAGOS.md §4).

Servicio de dominio SIN rutas (Fase 1). Funciones puras sobre ``db`` que operan
la transición:

    pending_payment → payment_submitted → active
    active → overdue → suspended
    overdue/suspended --pago--> payment_submitted --verify--> active
    cualquiera (no terminal) → cancelled

Convención del proyecto: los servicios devuelven docs crudos de Mongo
(``_id: ObjectId``, ``datetime`` nativos). La serialización Pydantic
``*Response`` llega en la Fase 3 (rutas), no aquí.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from config.settings import get_settings
from src.app.core.outbox import enqueue_audit_log
from src.app.modules.property_approval.pricing import (
    ANNUAL_DISCOUNT_FACTOR,
    available_plans,
)
from src.app.modules.subscriptions.notifications import (
    notify_overdue,
    notify_payment_received,
    notify_payment_rejected,
    notify_payment_verified,
    notify_suspended,
)

# ── Estados de la suscripción ─────────────────────────────────────────
STATUS_PENDING_PAYMENT = "pending_payment"
STATUS_PAYMENT_SUBMITTED = "payment_submitted"
STATUS_ACTIVE = "active"
STATUS_OVERDUE = "overdue"
STATUS_SUSPENDED = "suspended"
STATUS_CANCELLED = "cancelled"

# ── Estados de factura / pago ─────────────────────────────────────────
INVOICE_UNPAID = "unpaid"
INVOICE_PAID = "paid"
INVOICE_OVERDUE = "overdue"
INVOICE_VOID = "void"

PAYMENT_PENDING_VERIFICATION = "pending_verification"
PAYMENT_VERIFIED = "verified"
PAYMENT_REJECTED = "rejected"

# ── Métodos de pago manuales (sin pasarela) ──────────────────────────
PAYMENT_METHODS: tuple[str, ...] = ("bank_transfer", "cash_deposit", "manual_online")

# Días de gracia de la primera factura. Fuente de verdad: settings
# ``SUBSCRIPTION_INITIAL_GRACE_DAYS`` (default 7). Se mantiene como fallback
# defensivo si el settings no está disponible (scripts aislados).
INITIAL_GRACE_DAYS = 7

# Gracia de impago: días desde el vencimiento de la factura antes de
# suspender el hotel (``overdue`` → ``suspended``). Fuente de verdad: settings
# ``SUBSCRIPTION_SUSPENSION_GRACE_DAYS`` (default 7).
SUSPENSION_GRACE_DAYS = 7

# Duración de un período por ciclo de facturación.
PERIOD_DAYS: dict[str, int] = {"monthly": 30, "annual": 365}

VALID_BANDS: tuple[int, ...] = (1, 2, 3, 4, 5, 6)
VALID_BILLING_CYCLES: tuple[str, ...] = ("monthly", "annual")


# ── Excepciones de dominio ────────────────────────────────────────────


class SubscriptionError(Exception):
    """Base de los errores de dominio de suscripciones."""


class SubscriptionNotFoundError(SubscriptionError):
    """No existe la suscripción / factura / pago referenciado."""


class SubscriptionConflictError(SubscriptionError):
    """Operación idempotente repetida o recurso en estado ya terminal."""


class SubscriptionTransitionError(SubscriptionError):
    """Transición de estado inválida según la máquina de estados."""


# ── Helpers ───────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(UTC)


def _naive_utc(dt: datetime) -> datetime:
    """Normaliza a datetime naive en UTC (Mongo guarda/lee naive UTC).

    El cliente Mongo del proyecto usa ``tz_aware=False``: los ``datetime`` que
    vienen de BD son naive UTC aunque ``_now()`` sea aware. Para comparar
    fechas de BD con ``now`` hay que normalizar ambos lados.
    """
    if dt.tzinfo is not None:
        return dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def _oid(value: Any) -> ObjectId:
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError) as exc:
        raise SubscriptionNotFoundError(f"Identificador inválido: {value!r}") from exc


def _plan_for_band(db, band: int) -> dict[str, Any] | None:
    for plan in available_plans(db):
        if int(plan.get("band", 0)) == int(band):
            return plan
    return None


def _get_subscription(db, subscription_id: Any) -> dict[str, Any]:
    sub = db.subscriptions.find_one({"_id": _oid(subscription_id)})
    if not sub:
        raise SubscriptionNotFoundError(f"Suscripción no encontrada: {subscription_id!r}")
    return sub


def _initial_grace_days() -> int:
    """Gracia inicial de la primera factura — settings, con fallback defensivo."""
    try:
        return max(0, int(get_settings().subscription_initial_grace_days))
    except (AttributeError, OSError, TypeError, ValueError):
        return INITIAL_GRACE_DAYS


def _suspension_grace_days() -> int:
    """Gracia de impago antes de suspender — settings, con fallback defensivo."""
    try:
        return max(0, int(get_settings().subscription_suspension_grace_days))
    except (AttributeError, OSError, TypeError, ValueError):
        return SUSPENSION_GRACE_DAYS


def _set_hotel_operational(db, prop_id: int, operational: bool) -> None:
    """Solo ``is_operational`` (suspensión/reactivación) — ``published`` intacto.

    Un hotel suspendido por impago sigue publicado (presencia pública intacta,
    PLAN §12 edge case 3); el gate operativo lo bloquea por ``is_operational``.
    """
    db.dim_hotels.update_one(
        {"prop_id": int(prop_id)},
        {"$set": {"is_operational": operational, "updated_at": _now()}},
    )


def _deactivate_hotel(db, prop_id: int) -> None:
    """Cancelación terminal: ``is_operational=false`` + ``published=false``."""
    db.dim_hotels.update_one(
        {"prop_id": int(prop_id)},
        {"$set": {"is_operational": False, "published": False, "updated_at": _now()}},
    )


def _latest_invoice(db, subscription_id: Any) -> dict[str, Any] | None:
    return db.subscription_invoices.find_one(
        {"subscription_id": _oid(subscription_id)},
        sort=[("created_at", -1)],
    )


def _apply_pending_override(db, sub: dict[str, Any], now: datetime) -> dict[str, Any]:
    """Aplica el override programado (preaviso) al llegar el siguiente ciclo.

    Consume ``pending_price_band`` / ``pending_price_usd``: actualiza banda y
    precio, limpia los campos pendientes y audita como ``system`` (transición
    de ciclo, no acción de un actor). Devuelve la suscripción ya actualizada;
    si no hay override pendiente, devuelve ``sub`` sin escribir ni auditar.
    """
    pending_band = sub.get("pending_price_band")
    pending_price = sub.get("pending_price_usd")
    if pending_band is None and pending_price is None:
        return sub

    set_fields: dict[str, Any] = {"updated_at": now}
    diff: dict[str, Any] = {}
    if pending_band is not None:
        band = int(pending_band)
        plan = _plan_for_band(db, band)
        set_fields["band"] = band
        set_fields["band_label"] = (plan or {}).get("label", "")
        diff["price_band"] = {"old": sub.get("band"), "new": band}
    if pending_price is not None:
        amount = float(pending_price)
        set_fields["price_usd"] = amount
        diff["price_usd"] = {"old": sub.get("price_usd"), "new": amount}

    db.subscriptions.update_one(
        {"_id": sub["_id"]},
        {
            "$set": set_fields,
            "$unset": {"pending_price_band": "", "pending_price_usd": ""},
        },
    )
    updated = {**sub, **set_fields}
    updated.pop("pending_price_band", None)
    updated.pop("pending_price_usd", None)
    _audit_subscription(
        db,
        sub=updated,
        action="price.override.applied",
        summary="Override programado aplicado en el siguiente ciclo.",
        diff=diff,
    )
    return updated


def _overdue_grace_expired(db, sub: dict[str, Any], now: datetime) -> bool:
    """True si la factura ``overdue`` más reciente agotó la gracia de impago."""
    overdue_inv = db.subscription_invoices.find_one(
        {"subscription_id": sub["_id"], "status": INVOICE_OVERDUE},
        sort=[("created_at", -1)],
    )
    due = (overdue_inv or {}).get("due_date")
    if not due:
        return False
    return _naive_utc(due) + timedelta(days=_suspension_grace_days()) <= _naive_utc(now)


def _notify_context(db, sub: dict[str, Any]) -> tuple[str, str]:
    """Resuelve (email del dueño, nombre del hotel) para las notificaciones.

    Best-effort por diseño (PLAN §8): un email vacío o un dueño/hotel ausente
    no rompe la transición — la función ``notify_*`` salta el envío si el
    destinatario es vacío.
    """
    owner = db.users.find_one({"_id": sub.get("owner_user_id")}, {"email": 1})
    email = (owner or {}).get("email") or ""
    hotel = db.dim_hotels.find_one(
        {"prop_id": sub.get("prop_id")}, {"hotel_name": 1, "display_name": 1}
    )
    hotel_name = (
        (hotel or {}).get("hotel_name")
        or (hotel or {}).get("display_name")
        or f"Hotel #{sub.get('prop_id')}"
    )
    return email, hotel_name


def _audit_subscription(
    db,
    *,
    sub: dict[str, Any],
    action: str,
    summary: str,
    changed_by: str = "system",
    diff: dict[str, Any] | None = None,
) -> None:
    """Best-effort audit trail para transiciones de suscripción (PLAN §4).

    Escribe ``audit_log`` con ``entity_type="subscription"`` vía el outbox
    (mismo patrón que ``hotel_registration``). Best-effort: un fallo no rompe
    la transición ya persistida.
    """
    entry: dict[str, Any] = {
        "timestamp": _now(),
        "prop_id": sub.get("prop_id"),
        "entity_type": "subscription",
        "entity_id": str(sub["_id"]),
        "action": action,
        "summary": summary,
        "changed_by": changed_by or "system",
    }
    if diff:
        entry["diff"] = diff
    enqueue_audit_log(db, entry)


# ── Catálogo de precios ───────────────────────────────────────────────


def plan_price(db, band: int, billing_cycle: str = "monthly") -> float:
    """Cuota del período para una banda + ciclo (catálogo ``pricing_plans``)."""
    plan = _plan_for_band(db, band)
    if not plan:
        return 0.0
    if billing_cycle == "annual":
        explicit = plan.get("annual_monthly_usd")
        if explicit is not None:
            return float(explicit)
        return float(round(float(plan.get("monthly_usd", 0)) * ANNUAL_DISCOUNT_FACTOR))
    return float(plan.get("monthly_usd", 0))


# ── Lectura ───────────────────────────────────────────────────────────


def get_subscription(
    db,
    *,
    subscription_id: Any = None,
    prop_id: int | None = None,
) -> dict[str, Any] | None:
    """Devuelve la suscripción (por id o por hotel) o ``None`` si no existe."""
    if subscription_id is not None:
        return db.subscriptions.find_one({"_id": _oid(subscription_id)})
    if prop_id is not None:
        return db.subscriptions.find_one({"prop_id": int(prop_id)})
    return None


# ── Transiciones ──────────────────────────────────────────────────────


def create_subscription(
    db,
    *,
    prop_id: int,
    owner_user_id: Any,
    band: int,
    billing_cycle: str = "monthly",
    price_usd: float | None = None,
    currency: str = "USD",
    payment_method: str | None = None,
    initial_status: str = STATUS_PENDING_PAYMENT,
) -> dict[str, Any]:
    """Crea la suscripción (una por hotel).

    Nace en ``pending_payment`` salvo ``initial_status="active"`` — escape
    hatch documentado para migraciones/backfill de hoteles aprobados antes de
    la Fase 2 (nunca para el flujo de aprobación normal).
    """
    prop_id = int(prop_id)
    band = int(band)
    if band not in VALID_BANDS:
        raise ValueError(f"Banda inválida: {band}. Valores permitidos: {VALID_BANDS}.")
    if billing_cycle not in VALID_BILLING_CYCLES:
        raise ValueError(
            f"Ciclo de facturación inválido: {billing_cycle}. "
            f"Valores permitidos: {VALID_BILLING_CYCLES}."
        )
    if initial_status not in (STATUS_PENDING_PAYMENT, STATUS_ACTIVE):
        raise ValueError(
            f"Estado inicial inválido: {initial_status}. "
            f"Valores permitidos: {STATUS_PENDING_PAYMENT!r}, {STATUS_ACTIVE!r}."
        )
    if db.subscriptions.find_one({"prop_id": prop_id}):
        raise SubscriptionConflictError(
            f"Ya existe una suscripción para el hotel {prop_id}."
        )

    plan = _plan_for_band(db, band)
    if price_usd is None:
        price_usd = plan_price(db, band, billing_cycle)
    now = _now()

    doc: dict[str, Any] = {
        "prop_id": prop_id,
        "owner_user_id": owner_user_id,
        "band": band,
        "band_label": (plan or {}).get("label", ""),
        "billing_cycle": billing_cycle,
        "price_usd": float(price_usd),
        "currency": currency,
        "payment_method": payment_method,
        "status": initial_status,
        "started_at": now,
        "current_period_start": now,
        "current_period_end": None,
        "renews_at": None,
        "price_band_override": False,
        "approval_notes": None,
        "created_at": now,
        "updated_at": now,
    }
    result = db.subscriptions.insert_one(doc)
    doc["_id"] = result.inserted_id
    _audit_subscription(
        db,
        sub=doc,
        action="subscription.created",
        summary=f"Suscripción creada para el hotel {prop_id} (banda {band}, {billing_cycle}).",
        diff={"band": band, "billing_cycle": billing_cycle, "status": initial_status},
    )
    return doc


def emit_invoice(
    db,
    *,
    subscription_id: Any,
    period_start: datetime | None = None,
    period_end: datetime | None = None,
    amount_usd: float | None = None,
    due_date: datetime | None = None,
) -> dict[str, Any]:
    """Emite la factura del período (``unpaid``) y avanza el período de la suscripción.

    Permitido en ``pending_payment`` (primera factura), ``active`` y ``overdue``
    (renovaciones). No se emite en ``payment_submitted`` (hay un comprobante
    pendiente de conciliación), ``suspended`` ni ``cancelled``.
    """
    sub = _get_subscription(db, subscription_id)
    if sub["status"] not in (STATUS_PENDING_PAYMENT, STATUS_ACTIVE, STATUS_OVERDUE):
        raise SubscriptionTransitionError(
            f"No se puede emitir factura en estado '{sub['status']}'."
        )

    now = _now()
    # Preaviso (PLAN §12 edge 6 / §6.4): aplicar el override programado al
    # llegar el límite del ciclo, antes de facturar el nuevo período.
    sub = _apply_pending_override(db, sub, now)

    # El período siguiente empieza donde terminó el anterior (``current_period_end``);
    # en la primera factura aún no hay fin, así que arranca en ``current_period_start``.
    # Esto avanza el período de verdad: no reusa el rango del período anterior.
    start = (
        period_start
        or sub.get("current_period_end")
        or sub.get("current_period_start")
        or now
    )
    if period_end is not None:
        end = period_end
    else:
        days = PERIOD_DAYS.get(sub.get("billing_cycle"), PERIOD_DAYS["monthly"])
        end = start + timedelta(days=days)
    amount = float(amount_usd if amount_usd is not None else sub.get("price_usd", 0))
    due = due_date or (now + timedelta(days=_initial_grace_days()))

    seq = db.subscription_invoices.count_documents({"prop_id": sub["prop_id"]}) + 1
    invoice_number = f"SUB-{sub['prop_id']}-{start:%Y%m}-{seq}"

    inv: dict[str, Any] = {
        "subscription_id": sub["_id"],
        "prop_id": sub["prop_id"],
        "invoice_number": invoice_number,
        "period_start": start,
        "period_end": end,
        "amount_usd": amount,
        "currency": sub.get("currency", "USD"),
        "status": INVOICE_UNPAID,
        "due_date": due,
        "paid_at": None,
        "payment_id": None,
        "created_at": now,
    }
    result = db.subscription_invoices.insert_one(inv)
    inv["_id"] = result.inserted_id

    db.subscriptions.update_one(
        {"_id": sub["_id"]},
        {
            "$set": {
                "current_period_start": start,
                "current_period_end": end,
                "renews_at": end,
                "updated_at": now,
            }
        },
    )
    _audit_subscription(
        db,
        sub=sub,
        action="invoice.emitted",
        summary=f"Factura {invoice_number} emitida por {amount:.2f} {sub.get('currency', 'USD')}.",
        diff={"invoice_number": invoice_number, "amount_usd": amount},
    )
    return inv


def submit_payment(
    db,
    *,
    subscription_id: Any,
    invoice_id: Any,
    method: str,
    reference: str = "",
    amount: float,
    changed_by: str = "system",
) -> dict[str, Any]:
    """Registra el comprobante del pago (``pending_verification``).

    Transición: ``pending_payment``/``overdue``/``suspended`` →
    ``payment_submitted``; desde ``active`` (renovación) la suscripción sigue
    ``active``. Idempotente por factura: un segundo comprobante pendiente para
    la misma factura → ``SubscriptionConflictError``.
    """
    sub = _get_subscription(db, subscription_id)
    if method not in PAYMENT_METHODS:
        raise ValueError(f"Método de pago inválido: {method}.")

    inv = db.subscription_invoices.find_one({"_id": _oid(invoice_id)})
    if not inv or inv.get("subscription_id") != sub["_id"]:
        raise SubscriptionNotFoundError("Factura no encontrada para esta suscripción.")
    if inv["status"] not in (INVOICE_UNPAID, INVOICE_OVERDUE):
        raise SubscriptionConflictError("La factura ya está pagada o anulada.")

    # Idempotencia ANTES del gate de estado: un segundo comprobante para la
    # misma factura es un conflicto, no una transición inválida (la primera
    # sumisión ya movió la suscripción a ``payment_submitted``).
    existing = db.subscription_payments.find_one(
        {"invoice_id": inv["_id"], "status": PAYMENT_PENDING_VERIFICATION}
    )
    if existing:
        raise SubscriptionConflictError(
            "Ya existe un comprobante pendiente de verificación para esta factura."
        )

    if sub["status"] not in (
        STATUS_PENDING_PAYMENT,
        STATUS_ACTIVE,
        STATUS_OVERDUE,
        STATUS_SUSPENDED,
    ):
        raise SubscriptionTransitionError(
            f"No se puede registrar un pago en estado '{sub['status']}'."
        )

    amount = float(amount)
    if amount <= 0:
        raise ValueError("El monto debe ser mayor a 0.")

    now = _now()
    pay: dict[str, Any] = {
        "subscription_id": sub["_id"],
        "invoice_id": inv["_id"],
        "prop_id": sub["prop_id"],
        "method": method,
        "reference": reference or "",
        "proof_file_id": None,
        "amount": amount,
        "status": PAYMENT_PENDING_VERIFICATION,
        "rejection_reason": None,
        "verified_by": None,
        "verified_at": None,
        "rejected_by": None,
        "rejected_at": None,
        "created_at": now,
    }
    result = db.subscription_payments.insert_one(pay)
    pay["_id"] = result.inserted_id

    new_status = sub["status"] if sub["status"] == STATUS_ACTIVE else STATUS_PAYMENT_SUBMITTED
    db.subscriptions.update_one(
        {"_id": sub["_id"]},
        {"$set": {"status": new_status, "updated_at": now}},
    )

    # Fase 7 (PLAN §8): notificar al dueño (best-effort, no rompe la transición).
    email, hotel_name = _notify_context(db, sub)
    notify_payment_received(
        email, hotel_name=hotel_name, amount=pay["amount"], reference=pay.get("reference") or ""
    )
    _audit_subscription(
        db,
        sub=sub,
        action="payment.submitted",
        summary=f"Comprobante {method} por {amount:.2f} registrado.",
        changed_by=changed_by,
        diff={"status": {"old": sub["status"], "new": new_status}, "amount": amount},
    )
    return pay


def choose_subscription(
    db,
    *,
    subscription_id: Any,
    band: int,
    billing_cycle: str,
    payment_method: str,
    changed_by: str = "system",
) -> dict[str, Any]:
    """Confirma el plan del dueño: banda derivada + ciclo + método de pago.

    La banda NO es de libre elección — debe coincidir con la banda derivada de
    las habitaciones (guardada en la suscripción al aprobar). Cambiar el ciclo
    con la suscripción ``active`` → ``SubscriptionConflictError`` (preaviso, se
    aplica al siguiente período).
    """
    sub = _get_subscription(db, subscription_id)
    band = int(band)
    if band not in VALID_BANDS:
        raise ValueError(f"Banda inválida: {band}. Valores permitidos: {VALID_BANDS}.")
    if band != int(sub.get("band", 0)):
        raise ValueError(
            f"El plan elegido (banda {band}) no corresponde a tu suscripción "
            f"(banda {sub.get('band')}). Tu plan se deriva de tus habitaciones."
        )
    if billing_cycle not in VALID_BILLING_CYCLES:
        raise ValueError(
            f"Ciclo de facturación inválido: {billing_cycle}. "
            f"Valores permitidos: {VALID_BILLING_CYCLES}."
        )
    if payment_method not in PAYMENT_METHODS:
        raise ValueError(f"Método de pago inválido: {payment_method}.")
    if sub["status"] == STATUS_ACTIVE and billing_cycle != sub.get("billing_cycle"):
        raise SubscriptionConflictError(
            "No se puede cambiar el ciclo de facturación con la suscripción activa. "
            "El cambio se aplicará en el siguiente período."
        )

    now = _now()
    price = plan_price(db, band, billing_cycle)
    db.subscriptions.update_one(
        {"_id": sub["_id"]},
        {
            "$set": {
                "billing_cycle": billing_cycle,
                "payment_method": payment_method,
                "price_usd": price,
                "updated_at": now,
            }
        },
    )
    _audit_subscription(
        db,
        sub=sub,
        action="plan.chosen",
        summary=f"Plan confirmado: banda {band}, {billing_cycle}, {payment_method}.",
        changed_by=changed_by,
        diff={"billing_cycle": billing_cycle, "payment_method": payment_method, "price_usd": price},
    )
    return {
        **sub,
        "billing_cycle": billing_cycle,
        "payment_method": payment_method,
        "price_usd": price,
    }


def verify_payment(
    db,
    *,
    payment_id: Any,
    verified_by: str = "system",
    allowed_prop_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Concilia un comprobante: pago ``verified`` + factura ``paid`` + suscripción ``active``.

    ``allowed_prop_ids`` (opcional) restringe el alcance para supervisores
    hotel-scoped (``gerente_hotel``): un pago fuera de sus hoteles responde el
    MISMO 404 que un id desconocido, sin filtrar existencia (plan §6.3).
    """
    pay = db.subscription_payments.find_one({"_id": _oid(payment_id)})
    if not pay:
        raise SubscriptionNotFoundError("Pago no encontrado.")
    if allowed_prop_ids is not None and int(pay.get("prop_id", 0)) not in allowed_prop_ids:
        raise SubscriptionNotFoundError("Pago no encontrado.")
    if pay["status"] != PAYMENT_PENDING_VERIFICATION:
        raise SubscriptionConflictError("El pago ya fue conciliado.")

    now = _now()
    db.subscription_payments.update_one(
        {"_id": pay["_id"]},
        {"$set": {"status": PAYMENT_VERIFIED, "verified_by": verified_by, "verified_at": now}},
    )
    inv = db.subscription_invoices.find_one({"_id": pay["invoice_id"]})
    if inv:
        db.subscription_invoices.update_one(
            {"_id": inv["_id"]},
            {"$set": {"status": INVOICE_PAID, "paid_at": now, "payment_id": pay["_id"]}},
        )
    sub = db.subscriptions.find_one({"_id": pay["subscription_id"]})
    if sub and sub["status"] != STATUS_CANCELLED:
        prev_status = sub["status"]
        db.subscriptions.update_one(
            {"_id": sub["_id"]},
            {"$set": {"status": STATUS_ACTIVE, "updated_at": now}},
        )
        # Reactivación operativa: cualquier pago conciliado devuelve el hotel a
        # operativo (pending/overdue/suspended → active). Renovación ya-active
        # no reescribe (no-op seguro de todas formas).
        if prev_status != STATUS_ACTIVE:
            _set_hotel_operational(db, sub["prop_id"], True)
        # Fase 7 (PLAN §8): notificar al dueño (best-effort).
        email, hotel_name = _notify_context(db, sub)
        notify_payment_verified(email, hotel_name=hotel_name)
        _audit_subscription(
            db,
            sub=sub,
            action="payment.verified",
            summary="Pago conciliado; suscripción activa.",
            changed_by=verified_by,
            diff={"status": {"old": prev_status, "new": STATUS_ACTIVE}},
        )
    return {
        **pay,
        "status": PAYMENT_VERIFIED,
        "verified_by": verified_by,
        "verified_at": now,
    }


def reject_payment(
    db,
    *,
    payment_id: Any,
    reason: str,
    rejected_by: str = "system",
    allowed_prop_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Rechaza un comprobante (motivo obligatorio) y devuelve a ``pending_payment``.

    ``allowed_prop_ids`` aplica el mismo scoping por hotel que ``verify_payment``.
    """
    clean_reason = (reason or "").strip()
    if not clean_reason:
        raise ValueError("El motivo del rechazo es obligatorio.")

    pay = db.subscription_payments.find_one({"_id": _oid(payment_id)})
    if not pay:
        raise SubscriptionNotFoundError("Pago no encontrado.")
    if allowed_prop_ids is not None and int(pay.get("prop_id", 0)) not in allowed_prop_ids:
        raise SubscriptionNotFoundError("Pago no encontrado.")
    if pay["status"] != PAYMENT_PENDING_VERIFICATION:
        raise SubscriptionConflictError("El pago ya fue conciliado.")

    now = _now()
    db.subscription_payments.update_one(
        {"_id": pay["_id"]},
        {
            "$set": {
                "status": PAYMENT_REJECTED,
                "rejection_reason": clean_reason,
                "rejected_by": rejected_by,
                "rejected_at": now,
            }
        },
    )
    sub = db.subscriptions.find_one({"_id": pay["subscription_id"]})
    if sub and sub["status"] == STATUS_PAYMENT_SUBMITTED:
        db.subscriptions.update_one(
            {"_id": sub["_id"]},
            {"$set": {"status": STATUS_PENDING_PAYMENT, "updated_at": now}},
        )
    # Fase 7 (PLAN §8): notificar al dueño con el motivo (best-effort).
    if sub:
        email, hotel_name = _notify_context(db, sub)
        notify_payment_rejected(email, hotel_name=hotel_name, reason=clean_reason)
        _audit_subscription(
            db,
            sub=sub,
            action="payment.rejected",
            summary="Comprobante rechazado.",
            changed_by=rejected_by,
            diff={"reason": clean_reason},
        )
    return {
        **pay,
        "status": PAYMENT_REJECTED,
        "rejection_reason": clean_reason,
        "rejected_by": rejected_by,
        "rejected_at": now,
    }


def mark_overdue(db, *, subscription_id: Any, now: datetime | None = None) -> dict[str, Any]:
    """``active`` → ``overdue`` (la factura impaga más reciente pasa a ``overdue``)."""
    sub = _get_subscription(db, subscription_id)
    if sub["status"] != STATUS_ACTIVE:
        raise SubscriptionTransitionError(
            f"Solo una suscripción 'active' puede pasar a 'overdue' (actual: {sub['status']!r})."
        )

    ts = now or _now()
    unpaid = db.subscription_invoices.find_one(
        {"subscription_id": sub["_id"], "status": INVOICE_UNPAID},
        sort=[("created_at", -1)],
    )
    if unpaid:
        db.subscription_invoices.update_one(
            {"_id": unpaid["_id"]},
            {"$set": {"status": INVOICE_OVERDUE}},
        )
    db.subscriptions.update_one(
        {"_id": sub["_id"]},
        {"$set": {"status": STATUS_OVERDUE, "updated_at": ts}},
    )

    # Fase 7 (PLAN §8): recordatorio de vencimiento (best-effort).
    email, hotel_name = _notify_context(db, sub)
    amount = (unpaid or {}).get("amount_usd", sub.get("price_usd", 0))
    due_date = (unpaid or {}).get("due_date")
    notify_overdue(email, hotel_name=hotel_name, amount=float(amount), due_date=due_date)
    _audit_subscription(
        db,
        sub=sub,
        action="overdue",
        summary=f"Factura vencida sin pago ({float(amount):.2f}).",
        diff={"status": {"old": STATUS_ACTIVE, "new": STATUS_OVERDUE}},
    )
    return {**sub, "status": STATUS_OVERDUE}


def suspend(db, *, subscription_id: Any) -> dict[str, Any]:
    """``overdue`` → ``suspended`` + ``is_operational=false`` (Fase 5).

    El hotel queda fuera de operaciones pero SIGUE publicado (§12 edge case 3):
    presencia pública intacta, operaciones bloqueadas por el gate existente.
    """
    sub = _get_subscription(db, subscription_id)
    if sub["status"] != STATUS_OVERDUE:
        raise SubscriptionTransitionError(
            f"Solo una suscripción 'overdue' puede suspenderse (actual: {sub['status']!r})."
        )
    now = _now()
    db.subscriptions.update_one(
        {"_id": sub["_id"]},
        {"$set": {"status": STATUS_SUSPENDED, "suspended_at": now, "updated_at": now}},
    )
    _set_hotel_operational(db, sub["prop_id"], False)

    # Fase 7 (PLAN §8): notificar la suspensión (best-effort).
    email, hotel_name = _notify_context(db, sub)
    inv = _latest_invoice(db, sub["_id"])
    amount = (inv or {}).get("amount_usd", sub.get("price_usd", 0))
    notify_suspended(email, hotel_name=hotel_name, amount=float(amount))
    _audit_subscription(
        db,
        sub=sub,
        action="suspended",
        summary=f"Hotel {sub['prop_id']} suspendido por impago.",
        diff={"status": {"old": STATUS_OVERDUE, "new": STATUS_SUSPENDED}},
    )
    return {**sub, "status": STATUS_SUSPENDED}


def cancel(db, *, subscription_id: Any, reason: str = "", changed_by: str = "system") -> dict[str, Any]:
    """Cancela la suscripción (terminal) + ``is_operational=false`` + ``published=false``."""
    sub = _get_subscription(db, subscription_id)
    if sub["status"] == STATUS_CANCELLED:
        raise SubscriptionConflictError("La suscripción ya está cancelada.")
    now = _now()
    db.subscriptions.update_one(
        {"_id": sub["_id"]},
        {
            "$set": {
                "status": STATUS_CANCELLED,
                "cancelled_reason": reason or None,
                "cancelled_at": now,
                "updated_at": now,
            }
        },
    )
    _deactivate_hotel(db, sub["prop_id"])
    _audit_subscription(
        db,
        sub=sub,
        action="subscription.cancelled",
        summary=f"Suscripción del hotel {sub['prop_id']} cancelada.",
        changed_by=changed_by,
        diff={"reason": reason or None},
    )
    return {**sub, "status": STATUS_CANCELLED}


def override_subscription(
    db,
    *,
    prop_id: int,
    price_band: int | None = None,
    price_usd: float | None = None,
    notes: str = "",
    changed_by: str = "system",
) -> dict[str, Any]:
    """Override de precio negociado (auditado, ``price_band_override=True``).

    Fase 4 (PLAN_SUSCRIPCION_Y_PAGOS.md §6.2) + preaviso (PLAN §12 edge 6 /
    §6.4): el admin/supervisor puede fijar una banda y/o un precio distinto al
    derivado de las habitaciones. Al menos uno de los dos campos es
    obligatorio; el ``notes`` se guarda para la auditoría.

    En una suscripción ``active`` el override NO se aplica a mitad de ciclo:
    se programa en ``pending_price_band`` / ``pending_price_usd`` y se aplica
    en el siguiente ``emit_invoice`` (nunca sin aviso). En los estados previos
    al primer ciclo se aplica de inmediato.
    """
    sub = get_subscription(db, prop_id=int(prop_id))
    if not sub:
        raise SubscriptionNotFoundError(
            f"Suscripción no encontrada para el hotel {int(prop_id)}."
        )
    if price_band is None and price_usd is None:
        raise ValueError("Indica price_band o price_usd (o ambos) para el override.")

    band: int | None = None
    if price_band is not None:
        band = int(price_band)
        if band not in VALID_BANDS:
            raise ValueError(f"Banda inválida: {band}. Valores permitidos: {VALID_BANDS}.")
    amount: float | None = None
    if price_usd is not None:
        amount = float(price_usd)
        if amount <= 0:
            raise ValueError("El precio del override debe ser mayor a 0.")

    now = _now()
    clean_notes = notes.strip()

    if sub["status"] == STATUS_ACTIVE:
        # Preaviso: se programa para el siguiente ciclo (nunca a mitad de ciclo).
        # El ``$set`` a ``None`` reemplaza el override pendiente completo.
        set_fields: dict[str, Any] = {
            "price_band_override": True,
            "pending_price_band": band,
            "pending_price_usd": amount,
            "updated_at": now,
        }
        if clean_notes:
            set_fields["approval_notes"] = clean_notes
        db.subscriptions.update_one({"_id": sub["_id"]}, {"$set": set_fields})
        _audit_subscription(
            db,
            sub=sub,
            action="price.override.scheduled",
            summary="Override programado para el siguiente ciclo (preaviso).",
            changed_by=changed_by,
            diff={
                "price_band": {"new": band},
                "price_usd": {"new": amount},
                "notes": clean_notes,
            },
        )
        return get_subscription(db, prop_id=int(prop_id))

    # Antes del primer ciclo (o estados sin ciclo en curso): aplicación inmediata.
    set_fields = {
        "price_band_override": True,
        "updated_at": now,
    }
    if band is not None:
        plan = _plan_for_band(db, band)
        set_fields["band"] = band
        set_fields["band_label"] = (plan or {}).get("label", "")
    if amount is not None:
        set_fields["price_usd"] = amount
    if clean_notes:
        set_fields["approval_notes"] = clean_notes

    # Aplicación inmediata supera cualquier override pendiente residual.
    db.subscriptions.update_one(
        {"_id": sub["_id"]},
        {
            "$set": set_fields,
            "$unset": {"pending_price_band": "", "pending_price_usd": ""},
        },
    )
    _audit_subscription(
        db,
        sub=sub,
        action="price.override",
        summary="Override de precio negociado aplicado.",
        changed_by=changed_by,
        diff={"price_band": {"new": band}, "price_usd": {"new": amount}, "notes": clean_notes},
    )
    return get_subscription(db, prop_id=int(prop_id))


def list_subscription_payments(
    db,
    *,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    prop_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Cola de conciliación: comprobantes de ``subscription_payments``.

    ``prop_ids`` replica el contrato de ``hotel_filter_from_user``:
    ``None`` = cross-hotel (rol no filtrado); ``[]`` = deny-by-default (rol
    restringido sin hoteles); ``[1, 2]`` = solo esos hoteles (plan §6.3).

    Devuelve ``{items, total, page, page_size}`` — el enriquecimiento (hotel,
    dueño, método) lo hace la ruta admin, no el servicio (este servicio
    devuelve docs crudos de Mongo, convención del proyecto).
    """
    page = max(1, int(page))
    page_size = max(1, min(100, int(page_size)))
    query: dict[str, Any] = {}
    if status:
        query["status"] = status
    if prop_ids is not None:
        query["prop_id"] = {"$in": list(prop_ids)}
    total = db.subscription_payments.count_documents(query)
    items = list(
        db.subscription_payments.find(query)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def sweep_due_subscriptions(
    db,
    *,
    now: datetime | None = None,
) -> dict[str, int]:
    """Evaluación perezosa de renovaciones y gracia de impago (Fase 5).

    Sin cron: se invoca desde el middleware en cada request autenticado (y desde
    scripts/tests). Idempotente — un segundo barrido inmediato no duplica facturas
    ni transiciones. Devuelve contadores por transición:

    - ``renewals``: ``active`` con ``renews_at`` vencido → emite la factura del
      período siguiente (si la anterior está pagada).
    - ``overdue``: ``active`` con factura ``unpaid`` vencida → ``overdue``.
    - ``suspended``: ``overdue`` con gracia agotada → ``suspended`` +
      ``is_operational=false``.

    El barrido NO emite facturas ni suspende: delega en ``emit_invoice`` /
    ``mark_overdue`` / ``suspend`` (que ya escriben ``is_operational`` y auditan).
    """
    ts = _naive_utc(now or _now())
    counts = {"renewals": 0, "overdue": 0, "suspended": 0}

    # 1) active: renovación (renews_at vencido) + vencimiento (due_date pasado).
    for sub in db.subscriptions.find({"status": STATUS_ACTIVE}):
        latest = _latest_invoice(db, sub["_id"])
        renews_at = sub.get("renews_at")
        if (
            (latest is None or latest["status"] == INVOICE_PAID)
            and renews_at is not None
            and _naive_utc(renews_at) <= ts
        ):
            emit_invoice(db, subscription_id=sub["_id"])
            counts["renewals"] += 1
            latest = _latest_invoice(db, sub["_id"])
        if (
            latest is not None
            and latest["status"] == INVOICE_UNPAID
            and latest.get("due_date") is not None
            and _naive_utc(latest["due_date"]) <= ts
        ):
            mark_overdue(db, subscription_id=sub["_id"])
            counts["overdue"] += 1

    # 2) overdue: gracia de impago agotada → suspended.
    for sub in db.subscriptions.find({"status": STATUS_OVERDUE}):
        if _overdue_grace_expired(db, sub, ts):
            suspend(db, subscription_id=sub["_id"])
            counts["suspended"] += 1

    return counts
