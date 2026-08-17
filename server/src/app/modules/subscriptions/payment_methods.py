"""Catálogo de métodos de pago manuales (PLAN_SUSCRIPCION_Y_PAGOS.md §7).

Sin pasarela bancaria: el dinero lo confirma un humano. El catálogo expone los
datos de la cuenta destino (banco, titular, número de cuenta e instrucciones)
que el dueño ve al pagar. Se siembra idempotente vía
``scripts/seed_payment_methods.py``; los valores canónicos viven aquí (mismo
patrón que ``property_approval/pricing.py``). Los ``details`` los completa/edita
el admin en la BD — nunca se hardcodean datos reales de cuenta en el código.
"""

from __future__ import annotations

from typing import Any

DEFAULT_PAYMENT_METHODS: list[dict[str, Any]] = [
    {
        "code": "bank_transfer",
        "label": "Transferencia bancaria",
        "sort_order": 1,
        "details": {
            "bank_name": "",
            "account_holder": "",
            "account_number": "",
            "instructions": "El administrador completará los datos de la cuenta destino.",
        },
    },
    {
        "code": "cash_deposit",
        "label": "Depósito en ventanilla",
        "sort_order": 2,
        "details": {
            "bank_name": "",
            "account_holder": "",
            "account_number": "",
            "instructions": "Deposita en ventanilla y registra la referencia del comprobante.",
        },
    },
    {
        "code": "manual_online",
        "label": "Pago en línea",
        "sort_order": 3,
        "details": {
            "instructions": "Realiza una transferencia en línea y registra la referencia.",
        },
    },
]


def available_payment_methods(db) -> list[dict[str, Any]]:
    """Catálogo ordenado por ``sort_order`` — DB primero, defaults como fallback."""
    methods = list(
        db.payment_methods.find({"is_active": {"$ne": False}}).sort("sort_order", 1)
    )
    if methods:
        return methods
    return [dict(m) for m in DEFAULT_PAYMENT_METHODS]
