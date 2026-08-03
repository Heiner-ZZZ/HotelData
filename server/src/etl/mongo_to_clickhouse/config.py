"""Configuración del pipeline ETL MongoDB → ClickHouse (capa táctica de KPIs).

Paquete independiente de ``ga03_airflow``: comparte la misma arquitectura de
archivos (config / extract / transform / load / reports / pipeline) pero NO
importa nada de GA03 — los patrones se replican a propósito para no acoplar.

Ver ``docs/PLAN_ETL_MONGO_TO_CLICKHOUSE.md`` para el diseño completo.
"""

from __future__ import annotations

from pathlib import Path

from config.settings import get_settings

PIPELINE = "mongo_to_clickhouse"

# El destino M2C es una capa táctica desnormalizada: no publica catálogos
# ``dim_*`` como tablas activas. Los KPIs conservan sus IDs para trazabilidad y
# también el label vigente que el ETL resuelve desde Mongo en la misma corrida.
# Las tablas dim_* antiguas pueden existir físicamente por compatibilidad, pero
# quedan fuera del paquete M2C y no se vuelven a cargar.
FACT_TABLES: tuple[str, ...] = (
    # Compatibilidad: ritmo de reservas por fecha de entrada.
    "kpi_booking_daily",
    # Revenue por cada noche real de estancia.
    "kpi_booking_nights_daily",
    # Disponibilidad física por día y tipo de habitación.
    "kpi_inventory_daily",
    # Tarifa publicada por día y plan; el origen no siempre aporta moneda/tipo.
    "kpi_rate_daily",
    # Tabla compuesta para ADR, ocupación, RevPAR y comparación de tarifa.
    "kpi_room_performance_daily",
    # Reputación táctica: solo agregado diario; ``reviews`` y ``fact_reviews``
    # permanecen operacionales en MongoDB y no se replican como detalle.
    "kpi_review_daily",
    # Resumen compacto para informes globales por mercado/destino.
    "kpi_funnel_daily",
    # Detalle táctico por hotel buscado, canal, mercado y destino.
    "kpi_funnel_property_channel_daily",
    # Operaciones: housekeeping, mantenimiento, transiciones observables,
    # inventario agregado y cargos por día/propiedad.
    "kpi_housekeeping_daily",
    # Facturación táctica: monto facturado por día × hotel × estado
    # (F1.4 — emisión, pago, pendiente y anulación).
    "kpi_invoice_daily",
    # Pagos tácticos por día × hotel × método × estado, con el contexto de
    # facturación del día (facturado/cobrado/pendiente) (F1.5).
    "kpi_payment_daily",
)

# Contrato activo: únicamente tablas KPI compactas, ya enriquecidas para
# consultas de informes sin JOIN ni segunda consulta a MongoDB.
ALL_TABLES: tuple[str, ...] = FACT_TABLES

# Colección en MongoDB donde se persiste la configuración del horario del DAG.
ETL_PIPELINE_CONFIG_COLLECTION = "etl_pipeline_config"
DEFAULT_SCHEDULE_CRON = "0 * * * *"  # cada hora en punto

INSERT_BATCH_SIZE = 5000
PIPELINE_PROGRESS_STEPS = {
    "validate_config": 5,
    "extract_mongo": 30,
    "transform": 55,
    "create_tables": 65,
    "load_clickhouse": 90,
    "quality_report": 95,
    "execution_report": 100,
}

# Orden y etiquetas del proceso que consume la UI de monitoreo.
# Mantenerlo aquí evita que el backend y el frontend describan etapas distintas.
PIPELINE_PROGRESS_ORDER: tuple[str, ...] = (
    "validate_config",
    "extract_mongo",
    "transform",
    "create_tables",
    "load_clickhouse",
    "quality_report",
    "execution_report",
)
PIPELINE_PROGRESS_LABELS: dict[str, str] = {
    "validate_config": "Validate config",
    "extract_mongo": "Extract MongoDB",
    "transform": "Transform",
    "create_tables": "Create tables",
    "load_clickhouse": "Load ClickHouse",
    "quality_report": "Quality checks",
    "execution_report": "Execution report",
}

# Colecciones operacionales usadas para limitar la resolución del hotel. Los
# catálogos de Mongo se consultan solo durante el ETL para resolver labels; no
# se publican como tablas M2C ni se mezclan con GA03.
OPERATIONAL_COLLECTIONS: tuple[str, ...] = (
    "booking_orders",
    "reservation_invoices",
    "reservation_payments",
    "reviews",
    "housekeeping_tasks",
    "maintenance_tasks",
    "room_status_log",
    "room_status_history",
    "room_inventory_calendar",
    "additional_charges",
    "fact_inventory",
    "stay_service_requests",
)


def paths() -> dict[str, Path]:
    """Rutas de estado y reportes (misma convención de carpetas que GA03)."""
    settings = get_settings()
    return {
        "state": settings.staging_dir / "m2c_execution_state.json",
        "progress": settings.reports_dir / "progreso_pipeline_m2c.json",
        "execution_report": settings.reports_dir / "reporte_ejecucion_m2c.json",
        "quality_report": settings.reports_dir / "reporte_calidad_m2c.json",
        "extract_json": settings.staging_dir / "m2c_extract.json",
        "transformed_json": settings.staging_dir / "m2c_transformed.json",
        "load_counts_json": settings.staging_dir / "m2c_load_counts.json",
    }


def pipeline_config_collection() -> str:
    return ETL_PIPELINE_CONFIG_COLLECTION
