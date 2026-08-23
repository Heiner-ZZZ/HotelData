/**
 * View model del dashboard estratégico (TAF14) — Vista A (hotel individual) y
 * Vista B (cartera). Sigue el MISMO principio que los informes tácticos
 * compuestos: cada dashboard = summary (KPIs) + series/serie (gráficos) +
 * rows (tabla de registros paginada). Consume SOLO las tablas `strat_*` de
 * ClickHouse vía /api/strategic/*.
 */

export type Trend = 'up' | 'down' | 'flat';
export type Semaforo = 'green' | 'yellow' | 'red';
export type Quadrant = 'estrella' | 'oportunidad' | 'consolidacion' | 'riesgo';

export interface StrategicKpi {
  id: string;
  label: string;
  value: number;
  unit: string;
  target: number | null;
  pctChange: number;
  trend: Trend;
  semaforo: Semaforo;
  detail: string;
}

export interface SeriesData {
  labels: string[];
  datasets: { label: string; data: number[] }[];
}

export interface Paginated<T> {
  rows: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

export interface BandaPrecio {
  p25: number;
  p50: number;
  p75: number;
}

export interface CompetitorMarker {
  propId: number;
  hotelLabel: string;
  lat: number | null;
  lng: number | null;
  adr: number;
  rating: number;
  distanceKm: number | null;
}

export interface Posicionamiento {
  rating: number;
  adr: number;
  ratingVariacion: number;
  adrVariacion: number;
  competitors: number;
  city: string;
  radioKm: number | null;
  adrPercentile: number | null;
  ratingPercentile: number | null;
  bandaPrecio: BandaPrecio | null;
  precioRelativoPct: number | null;
  diagnosis: string;
  decision: string;
  ownLat: number | null;
  ownLng: number | null;
  competitorsMarkers: CompetitorMarker[];
}

export interface PosicionamientoRow {
  month: string;
  rating: number;
  adr: number;
  respuesta: number;
}

export interface RankingEntry {
  entidad: string;
  valor: number;
  unidad: string;
  variacion: number;
  motivo: string;
  decision: string;
}

export interface RankingGroup {
  codigo: string;
  titulo: string;
  criterio: string;
  rows: RankingEntry[];
}

export interface Rankings {
  kpis: StrategicKpi[];
  series: SeriesData;
  groups: RankingGroup[];
}

export interface StrategicSummary {
  kpis: StrategicKpi[];
  hoteles: number;
  posicionamiento: Posicionamiento | null;
}

export interface PlanRow {
  label: string;
  bookings: number;
  roomNights: number;
  revenueBruto: number;
  revenueNeto: number;
  descuento: number;
  descuentoPct: number;
  adr: number;
}

export interface CarteraRow {
  propId: number;
  hotelLabel: string;
  bookings: number;
  roomNights: number;
  revenueBruto: number;
  revenueNeto: number;
  descuento: number;
  descuentoPct: number;
  adr: number;
  ocupacionPct: number;
  revpar: number;
  variacion: number;
}

export interface HotelRow {
  month: string;
  bookings: number;
  roomNights: number;
  revenueBruto: number;
  revenueNeto: number;
  descuento: number;
  adr: number;
  ocupacionPct: number;
  revpar: number;
  cancelacionPct: number;
}

export interface MarketEntry {
  destination: string;
  searches: number;
  clicks: number;
  reservations: number;
  revenue: number;
  conversionPct: number;
  growthPct: number;
  positionPct: number;
  quadrant: Quadrant;
  decision: string;
}

export interface StrategicPortfolio {
  available: boolean;
  message?: string;
  dateFrom: string;
  dateTo: string;
  propId: number | null;
  summary: StrategicSummary;
  series: SeriesData;
  rows: Paginated<CarteraRow>;
  planes: Paginated<PlanRow>;
  rankings: Rankings;
}

export interface StrategicHotel {
  available: boolean;
  message?: string;
  dateFrom: string;
  dateTo: string;
  propId: number;
  summary: StrategicSummary;
  serie: SeriesData;
  posicionamientoSerie: SeriesData;
  posicionamientoRows: PosicionamientoRow[];
  rows: Paginated<HotelRow>;
  planes: Paginated<PlanRow>;
}

export type StrategicMarkets = {
  available: boolean;
  message?: string;
  dateFrom: string;
  dateTo: string;
  summary: StrategicSummary;
  series: SeriesData;
  rows: Paginated<MarketEntry>;
};

export const QUADRANT_META: Record<Quadrant, { label: string; icon: string; tone: string }> = {
  estrella: { label: 'Estrella', icon: 'star', tone: 'success' },
  oportunidad: { label: 'Oportunidad', icon: 'trending_up', tone: 'accent' },
  consolidacion: { label: 'Consolidación', icon: 'balance', tone: 'warning' },
  riesgo: { label: 'Riesgo', icon: 'warning', tone: 'danger' },
};
