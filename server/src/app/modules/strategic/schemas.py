"""Modelos Pydantic ``*Response`` del API estratégico TAF14 (Vista A y B).

Contrato compuesto (mismo principio que los informes tácticos): cada endpoint
devuelve ``summary`` (KPIs en cajas separadas) + ``series``/``serie``
(gráficos) + ``rows`` (tabla de registros paginada). Los 7 informes dictados
en TAF14: Vista A = IE-H01/IE-H02; Vista B = IE-G01 (KPIs), IE-G02
(rankings R-G01..R-G06), IE-G03, IE-G04, IE-G05. El BSC quedó fuera por
decisión del dueño (patrón Z). Los campos de datos quedan vacíos cuando
ClickHouse no responde (``available: false`` + ``message``, nunca 500).
Convención del proyecto: ``ConfigDict(populate_by_name=True)`` +
``model_rebuild()`` al final.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class StrategicKpiResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    label: str
    value: float
    unit: str = ""
    target: float | None = None
    pct_change: float = 0.0
    trend: str = "flat"
    semaforo: str = "yellow"
    detail: str = ""


class SeriesDatasetResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    label: str
    data: list[float] = []


class SeriesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    labels: list[str] = []
    datasets: list[SeriesDatasetResponse] = []


class PaginationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    has_next: bool = False
    has_prev: bool = False


class PosicionamientoResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    rating: float = 0.0
    adr: float = 0.0
    rating_variacion: float = 0.0
    adr_variacion: float = 0.0
    diagnosis: str = ""
    decision: str = ""


class StrategicSummaryResponse(BaseModel):
    """Resumen compuesto: KPIs + contexto del dashboard (hoteles o
    posicionamiento). ``kpis`` es la tira del patrón Z."""
    model_config = ConfigDict(populate_by_name=True)
    kpis: list[StrategicKpiResponse] = []
    hoteles: int = 0
    posicionamiento: PosicionamientoResponse | None = None


class PlanRowResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    label: str
    bookings: int = 0
    room_nights: int = 0
    revenue_bruto: float = 0.0
    revenue_neto: float = 0.0
    descuento: float = 0.0
    descuento_pct: float = 0.0
    adr: float = 0.0


class PlanListResponse(PaginationResponse):
    model_config = ConfigDict(populate_by_name=True)
    rows: list[PlanRowResponse] = []


class CarteraRowResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    prop_id: int
    hotel_label: str = ""
    bookings: int = 0
    room_nights: int = 0
    revenue_bruto: float = 0.0
    revenue_neto: float = 0.0
    descuento: float = 0.0
    descuento_pct: float = 0.0
    adr: float = 0.0
    ocupacion_pct: float = 0.0
    revpar: float = 0.0
    variacion: float = 0.0


class HotelRowResponse(BaseModel):
    """Tabla de registros de la Vista A: una fila por mes del hotel."""
    model_config = ConfigDict(populate_by_name=True)
    month: str
    bookings: int = 0
    room_nights: int = 0
    revenue_bruto: float = 0.0
    revenue_neto: float = 0.0
    descuento: float = 0.0
    adr: float = 0.0
    ocupacion_pct: float = 0.0
    revpar: float = 0.0
    cancelacion_pct: float = 0.0


class MarketEntryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    destination: str
    searches: int = 0
    clicks: int = 0
    reservations: int = 0
    revenue: float = 0.0
    conversion_pct: float = 0.0
    growth_pct: float = 0.0
    position_pct: float = 0.0
    quadrant: str = "riesgo"
    decision: str = ""


class RankingEntryResponse(BaseModel):
    """Fila de un ranking IE-G02: entidad, valor, variación, motivo y decisión."""
    model_config = ConfigDict(populate_by_name=True)
    entidad: str
    valor: float = 0.0
    unidad: str = ""
    variacion: float = 0.0
    motivo: str = ""
    decision: str = ""


class RankingGroupResponse(BaseModel):
    """Grupo de ranking R-G01..R-G06 con su criterio de ordenamiento."""
    model_config = ConfigDict(populate_by_name=True)
    codigo: str
    titulo: str
    criterio: str
    rows: list[RankingEntryResponse] = []


class RankingsResponse(BaseModel):
    """IE-G02 compuesto: KPIs por ranking + serie (top hoteles) + grupos."""
    model_config = ConfigDict(populate_by_name=True)
    kpis: list[StrategicKpiResponse] = []
    series: SeriesResponse = SeriesResponse()
    groups: list[RankingGroupResponse] = []


class PosicionamientoRowResponse(BaseModel):
    """Registro mensual del posicionamiento (IE-H02): rating, ADR, respuesta."""
    model_config = ConfigDict(populate_by_name=True)
    month: str
    rating: float = 0.0
    adr: float = 0.0
    respuesta: float = 0.0


class StrategicPortfolioResponse(PaginationResponse):
    """Vista B — cartera compuesta: summary.kpis (IE-G01) + series + rows
    (tabla por hotel, IE-G03) + planes (IE-G03) + rankings (IE-G02)."""
    model_config = ConfigDict(populate_by_name=True)
    available: bool
    source: str = "clickhouse"
    date_from: str = ""
    date_to: str = ""
    prop_id: int | None = None
    message: str | None = None
    summary: StrategicSummaryResponse = StrategicSummaryResponse()
    series: SeriesResponse = SeriesResponse()
    rows: list[CarteraRowResponse] = []
    planes: PlanListResponse = PlanListResponse()
    rankings: RankingsResponse = RankingsResponse()


class StrategicHotelResponse(PaginationResponse):
    """Vista A — hotel compuesto (IE-H01/H02): summary.kpis (+ posicionamiento
    Z: serie + tabla) + serie + rows (registros mensuales) + planes
    (rentabilidad por tipo)."""
    model_config = ConfigDict(populate_by_name=True)
    available: bool
    source: str = "clickhouse"
    date_from: str = ""
    date_to: str = ""
    prop_id: int
    message: str | None = None
    summary: StrategicSummaryResponse = StrategicSummaryResponse()
    serie: SeriesResponse = SeriesResponse()
    posicionamiento_serie: SeriesResponse = SeriesResponse()
    posicionamiento_rows: list[PosicionamientoRowResponse] = []
    rows: list[HotelRowResponse] = []
    planes: PlanListResponse = PlanListResponse()


class StrategicMarketsResponse(PaginationResponse):
    """Vista B — mercados compuesto (IE-G04): summary.kpis (demanda) + series
    + rows (tabla por destino con cuadrante)."""
    model_config = ConfigDict(populate_by_name=True)
    available: bool
    source: str = "clickhouse"
    date_from: str = ""
    date_to: str = ""
    prop_id: int | None = None
    message: str | None = None
    summary: StrategicSummaryResponse = StrategicSummaryResponse()
    series: SeriesResponse = SeriesResponse()
    rows: list[MarketEntryResponse] = []


StrategicKpiResponse.model_rebuild()
SeriesDatasetResponse.model_rebuild()
SeriesResponse.model_rebuild()
PaginationResponse.model_rebuild()
PosicionamientoResponse.model_rebuild()
StrategicSummaryResponse.model_rebuild()
PlanRowResponse.model_rebuild()
PlanListResponse.model_rebuild()
CarteraRowResponse.model_rebuild()
HotelRowResponse.model_rebuild()
MarketEntryResponse.model_rebuild()
RankingEntryResponse.model_rebuild()
RankingGroupResponse.model_rebuild()
RankingsResponse.model_rebuild()
PosicionamientoRowResponse.model_rebuild()
StrategicPortfolioResponse.model_rebuild()
StrategicHotelResponse.model_rebuild()
StrategicMarketsResponse.model_rebuild()
