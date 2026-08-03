"""Tests del dashboard táctico de facturación (F1.4).

Cubren las funciones puras del servicio (resumen y serie diaria) sin depender
de ClickHouse levantado. La conectividad real se cubre con la prueba de
integración del pipeline M2C.
"""

from __future__ import annotations

from src.app.modules.billing.service.lifecycle.analytics import (
    _series,
    _series_payments,
    _summarise,
    _summarise_payments,
)


def _row(
    date: str,
    prop: int,
    hotel: str,
    status: str,
    count: int,
    total: float,
    paid: float = 0,
    pending: float = 0,
    cancelled: float = 0,
) -> dict:
    return {
        "date": date, "prop_id": prop, "hotel_label": hotel, "status": status,
        "invoice_count": count, "subtotal": round(total * 0.9, 2),
        "taxes": round(total * 0.1, 2), "total": total,
        "paid_total": paid, "pending_total": pending, "cancelled_total": cancelled,
    }


def test_summarise_totals_by_status_and_by_hotel():
    rows = [
        _row("2026-08-01", 1, "Hotel A", "issued", 2, 200.0, pending=200.0),
        _row("2026-08-01", 1, "Hotel A", "paid", 1, 100.0, paid=100.0),
        _row("2026-08-02", 2, "Hotel B", "cancelled", 1, 50.0, cancelled=50.0),
    ]
    summary = _summarise(rows)
    assert summary["invoice_count"] == 4
    assert summary["total_amount"] == 350.0
    assert summary["subtotal"] == 315.0
    assert summary["taxes"] == 35.0
    assert summary["paid_total"] == 100.0
    assert summary["pending_total"] == 200.0
    assert summary["cancelled_total"] == 50.0
    assert summary["by_status"]["issued"]["count"] == 2
    assert summary["by_status"]["paid"]["label"] == "Pagada"
    # by_hotel ordenado por total descendente.
    assert [h["hotel_label"] for h in summary["by_hotel"]] == ["Hotel A", "Hotel B"]
    assert summary["by_hotel"][0]["invoice_count"] == 3


def test_summarise_empty_returns_zeros():
    summary = _summarise([])
    assert summary["invoice_count"] == 0
    assert summary["total_amount"] == 0.0
    assert summary["by_status"] == {}
    assert summary["by_hotel"] == []


def _pay_row(
    date: str,
    prop: int,
    hotel: str,
    method: str,
    status: str,
    count: int,
    paid: float = 0,
    refunded: float = 0,
    failed: float = 0,
    invoiced: float = 0,
    collected: float = 0,
) -> dict:
    return {
        "date": date, "prop_id": prop, "hotel_label": hotel, "method": method,
        "status": status, "payment_count": count, "paid_amount": paid,
        "refunded_amount": refunded, "failed_amount": failed,
        "invoiced_amount": invoiced, "collected_amount": collected,
        "outstanding_amount": round(invoiced - collected, 2),
    }


def test_payments_summarise_crosses_invoices_and_payments():
    # Día 1: facturación 200, cobrado 100 (contexto repetido en cada fila).
    rows = [
        _pay_row("2026-08-01", 1, "Hotel A", "card", "confirmed", 1, paid=60, invoiced=200, collected=100),
        _pay_row("2026-08-01", 1, "Hotel A", "cash", "confirmed", 1, paid=40, invoiced=200, collected=100),
        _pay_row("2026-08-02", 1, "Hotel A", "card", "refunded", 1, refunded=20, invoiced=0, collected=0),
        _pay_row("2026-08-03", 2, "Hotel B", "", "no_payment", 0, invoiced=50, collected=0),
    ]
    summary = _summarise_payments(rows)
    assert summary["payment_count"] == 3
    assert summary["paid_amount"] == 100.0
    assert summary["refunded_amount"] == 20.0
    assert summary["failed_amount"] == 0.0
    # El contexto facturado/cobrado se agrega sobre (fecha, prop) únicos,
    # NO por fila de método: 200 + 0 + 50 = 250 facturado.
    assert summary["invoiced_amount"] == 250.0
    assert summary["collected_amount"] == 100.0
    assert summary["outstanding_amount"] == 150.0
    methods = {m["method"]: m["amount"] for m in summary["by_method"]}
    assert methods["card"] == 60.0
    assert methods["cash"] == 40.0
    assert summary["by_hotel"][0]["collected_amount"] == 100.0


def test_payments_series_daily_uses_distinct_day_context():
    rows = [
        _pay_row("2026-08-01", 1, "Hotel A", "card", "confirmed", 1, paid=60, invoiced=200, collected=100),
        _pay_row("2026-08-01", 1, "Hotel A", "cash", "confirmed", 1, paid=40, invoiced=200, collected=100),
        _pay_row("2026-08-02", 2, "Hotel B", "", "no_payment", 0, invoiced=50, collected=0),
    ]
    series = _series_payments(rows)
    assert series["labels"] == ["2026-08-01", "2026-08-02"]
    datasets = {d["label"]: d["data"] for d in series["datasets"]}
    assert datasets["Cobrado"] == [100.0, 0.0]
    assert datasets["Facturado"] == [200.0, 50.0]
    assert datasets["Pendiente"] == [100.0, 50.0]


def test_series_daily_evolution_sums_by_date():
    rows = [
        _row("2026-08-01", 1, "Hotel A", "issued", 2, 200.0, pending=200.0),
        _row("2026-08-02", 1, "Hotel A", "paid", 1, 100.0, paid=100.0),
        _row("2026-08-02", 2, "Hotel B", "paid", 1, 50.0, paid=50.0),
    ]
    series = _series(rows)
    assert series["labels"] == ["2026-08-01", "2026-08-02"]
    datasets = {d["label"]: d["data"] for d in series["datasets"]}
    assert datasets["Facturado"] == [200.0, 150.0]
    assert datasets["Pagado"] == [0.0, 150.0]
    assert datasets["Pendiente"] == [200.0, 0.0]
