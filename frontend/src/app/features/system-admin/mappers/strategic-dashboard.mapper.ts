import type {
  CarteraRow,
  HotelRow,
  MarketEntry,
  PlanRow,
  Posicionamiento,
  PosicionamientoRow,
  RankingEntry,
  RankingGroup,
  Rankings,
  StrategicHotel,
  StrategicKpi,
  StrategicMarkets,
  StrategicPortfolio,
  StrategicSummary,
} from '../models/strategic-dashboard.model';

/* eslint-disable @typescript-eslint/no-explicit-any */

const asNum = (v: any): number => Number(v ?? 0);

function mapKpi(raw: any): StrategicKpi {
  return {
    id: raw.id,
    label: raw.label,
    value: asNum(raw.value),
    unit: raw.unit ?? '',
    target: raw.target == null ? null : asNum(raw.target),
    pctChange: asNum(raw.pct_change),
    trend: raw.trend ?? 'flat',
    semaforo: raw.semaforo ?? 'yellow',
    detail: raw.detail ?? '',
  };
}

function mapSummary(raw: any): StrategicSummary {
  return {
    kpis: (raw?.kpis ?? []).map(mapKpi),
    hoteles: asNum(raw?.hoteles),
    posicionamiento: raw?.posicionamiento ? mapPosicionamiento(raw.posicionamiento) : null,
  };
}

function mapSeries(raw: any): { labels: string[]; datasets: { label: string; data: number[] }[] } {
  return {
    labels: (raw?.labels ?? []).map(String),
    datasets: (raw?.datasets ?? []).map((d: any) => ({
      label: d.label,
      data: (d.data ?? []).map(asNum),
    })),
  };
}

function mapPaginated(raw: any): { total: number; page: number; pageSize: number; totalPages: number; hasNext: boolean; hasPrev: boolean } {
  return {
    total: asNum(raw.total),
    page: asNum(raw.page),
    pageSize: asNum(raw.page_size),
    totalPages: asNum(raw.total_pages),
    hasNext: Boolean(raw.has_next),
    hasPrev: Boolean(raw.has_prev),
  };
}

function mapPosicionamiento(raw: any): Posicionamiento {
  return {
    rating: asNum(raw?.rating),
    adr: asNum(raw?.adr),
    ratingVariacion: asNum(raw?.rating_variacion),
    adrVariacion: asNum(raw?.adr_variacion),
    competitors: asNum(raw?.competitors),
    city: raw?.city ?? '',
    radioKm: raw?.radio_km ?? null,
    adrPercentile: raw?.adr_percentile ?? null,
    ratingPercentile: raw?.rating_percentile ?? null,
    bandaPrecio: raw?.banda_precio
      ? {
          p25: asNum(raw.banda_precio.p25),
          p50: asNum(raw.banda_precio.p50),
          p75: asNum(raw.banda_precio.p75),
        }
      : null,
    precioRelativoPct: raw?.precio_relativo_pct ?? null,
    diagnosis: raw?.diagnosis ?? '',
    decision: raw?.decision ?? '',
    ownLat: raw?.own_lat ?? null,
    ownLng: raw?.own_lng ?? null,
    competitorsMarkers: (raw?.competitors_markers ?? []).map((m: any) => ({
      propId: asNum(m?.prop_id),
      hotelLabel: m?.hotel_label ?? '',
      lat: m?.lat ?? null,
      lng: m?.lng ?? null,
      adr: asNum(m?.adr),
      rating: asNum(m?.rating),
      distanceKm: m?.distance_km ?? null,
    })),
  };
}

function mapPlanRow(raw: any): PlanRow {
  return {
    label: raw.label,
    bookings: asNum(raw.bookings),
    roomNights: asNum(raw.room_nights),
    revenueBruto: asNum(raw.revenue_bruto),
    revenueNeto: asNum(raw.revenue_neto),
    descuento: asNum(raw.descuento),
    descuentoPct: asNum(raw.descuento_pct),
    adr: asNum(raw.adr),
  };
}

function mapCarteraRow(raw: any): CarteraRow {
  return {
    propId: asNum(raw.prop_id),
    hotelLabel: raw.hotel_label ?? `Hotel #${raw.prop_id}`,
    bookings: asNum(raw.bookings),
    roomNights: asNum(raw.room_nights),
    revenueBruto: asNum(raw.revenue_bruto),
    revenueNeto: asNum(raw.revenue_neto),
    descuento: asNum(raw.descuento),
    descuentoPct: asNum(raw.descuento_pct),
    adr: asNum(raw.adr),
    ocupacionPct: asNum(raw.ocupacion_pct),
    revpar: asNum(raw.revpar),
    variacion: asNum(raw.variacion),
  };
}

function mapHotelRow(raw: any): HotelRow {
  return {
    month: raw.month,
    bookings: asNum(raw.bookings),
    roomNights: asNum(raw.room_nights),
    revenueBruto: asNum(raw.revenue_bruto),
    revenueNeto: asNum(raw.revenue_neto),
    descuento: asNum(raw.descuento),
    adr: asNum(raw.adr),
    ocupacionPct: asNum(raw.ocupacion_pct),
    revpar: asNum(raw.revpar),
    cancelacionPct: asNum(raw.cancelacion_pct),
  };
}

function mapMarketEntry(raw: any): MarketEntry {
  return {
    destination: raw.destination,
    searches: asNum(raw.searches),
    clicks: asNum(raw.clicks),
    reservations: asNum(raw.reservations),
    revenue: asNum(raw.revenue),
    conversionPct: asNum(raw.conversion_pct),
    growthPct: asNum(raw.growth_pct),
    positionPct: asNum(raw.position_pct),
    quadrant: raw.quadrant,
    decision: raw.decision ?? '',
  };
}

function mapPosicionamientoRow(raw: any): PosicionamientoRow {
  return {
    month: raw.month,
    rating: asNum(raw.rating),
    adr: asNum(raw.adr),
    respuesta: asNum(raw.respuesta),
  };
}

function mapRankingEntry(raw: any): RankingEntry {
  return {
    entidad: raw.entidad,
    valor: asNum(raw.valor),
    unidad: raw.unidad ?? '',
    variacion: asNum(raw.variacion),
    motivo: raw.motivo ?? '',
    decision: raw.decision ?? '',
  };
}

function mapRankingGroup(raw: any): RankingGroup {
  return {
    codigo: raw.codigo,
    titulo: raw.titulo,
    criterio: raw.criterio,
    rows: (raw.rows ?? []).map(mapRankingEntry),
  };
}

function mapRankings(raw: any): Rankings {
  return {
    kpis: (raw?.kpis ?? []).map(mapKpi),
    series: mapSeries(raw?.series),
    groups: (raw?.groups ?? []).map(mapRankingGroup),
  };
}

export function mapStrategicPortfolio(dto: any): StrategicPortfolio {
  return {
    available: Boolean(dto?.available),
    message: dto?.message ?? undefined,
    dateFrom: dto?.date_from ?? '',
    dateTo: dto?.date_to ?? '',
    propId: dto?.prop_id ?? null,
    summary: mapSummary(dto?.summary),
    series: mapSeries(dto?.series),
    rows: {
      rows: (dto?.rows ?? []).map(mapCarteraRow),
      ...mapPaginated(dto),
    },
    planes: {
      rows: (dto?.planes?.rows ?? []).map(mapPlanRow),
      ...mapPaginated(dto?.planes ?? {}),
    },
    rankings: mapRankings(dto?.rankings),
  };
}

export function mapStrategicHotel(dto: any): StrategicHotel {
  return {
    available: Boolean(dto?.available),
    message: dto?.message ?? undefined,
    dateFrom: dto?.date_from ?? '',
    dateTo: dto?.date_to ?? '',
    propId: Number(dto?.prop_id ?? 0),
    summary: mapSummary(dto?.summary),
    serie: mapSeries(dto?.serie),
    posicionamientoSerie: mapSeries(dto?.posicionamiento_serie),
    posicionamientoRows: (dto?.posicionamiento_rows ?? []).map(mapPosicionamientoRow),
    rows: {
      rows: (dto?.rows ?? []).map(mapHotelRow),
      ...mapPaginated(dto),
    },
    planes: {
      rows: (dto?.planes?.rows ?? []).map(mapPlanRow),
      ...mapPaginated(dto?.planes ?? {}),
    },
  };
}

export function mapStrategicMarkets(dto: any): StrategicMarkets {
  return {
    available: Boolean(dto?.available),
    message: dto?.message ?? undefined,
    dateFrom: dto?.date_from ?? '',
    dateTo: dto?.date_to ?? '',
    summary: mapSummary(dto?.summary),
    series: mapSeries(dto?.series),
    rows: {
      rows: (dto?.rows ?? []).map(mapMarketEntry),
      ...mapPaginated(dto),
    },
  };
}
