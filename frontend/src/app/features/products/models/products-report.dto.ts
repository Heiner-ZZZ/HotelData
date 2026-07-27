/**
 * DTOs for the 3 product report endpoints (margin / COGS / stock-value).
 *
 * These mirror the backend Pydantic response_model shapes in
 * `server/src/app/modules/partner/routes/hotel_products.py`.
 *
 * Convention: snake_case to match the raw HTTP wire format (Angular 22
 * convention; convert in `reportMappers.ts` if a domain-shape helper is
 * needed).
 */

// ─── Margin Report ───────────────────────────────────────────────────────

/**
 * Mirror of Pydantic ``MarginSummaryResponse`` in
 * ``server/src/app/modules/partner/routes/hotel_products.py`` —
 * KEEP IN SYNC.
 *
 * ``active_products`` intentionally omitted: the backend report filter
 * already excludes archived + inactive, so the count is redundant with
 * ``total_products``. The raw wire JSON will not contain
 * ``active_products``; do not add it back without first restoring the
 * field on the backend.
 */
export interface MarginSummaryDto {
  total_products: number;
  total_margin_abs: number;
  total_unit_price: number;
  global_margin_pct: number;
}

export interface MarginReportItemDto {
  id: string;
  product_id: string;
  name: string;
  category: string;
  type: string;
  cost_price: number;
  unit_price: number;
  margin_abs: number;
  margin_pct: number;
  quantity_available: number;
}

export interface MarginReportDto {
  summary: MarginSummaryDto;
  items: MarginReportItemDto[];
}

// ─── COGS Report ─────────────────────────────────────────────────────────

/**
 * Method used by the backend to drain inventory layers for COGS.
 * KEEP IN SYNC with the ``method`` query param regex in
 * ``server/src/app/modules/partner/routes/hotel_products.py``
 * ``get_cogs_report`` endpoint and the ``method`` parameter of
 * ``compute_cogs_report()`` / ``drain_layers_for_sale()``.
 *
 * ``fifo`` — oldest layer first (GAAP-aligned, default).
 * ``lifo`` — newest layer first.
 * ``approx`` — skip layer drain; multiply by current
 *             ``hotel_products.cost_price`` (Fase 5 fallback).
 */
export type CogsMethod = 'fifo' | 'lifo' | 'approx';

export const COGS_METHODS: { key: CogsMethod; label: string }[] = [
  { key: 'fifo', label: 'FIFO (oldest)' },
  { key: 'lifo', label: 'LIFO (newest)' },
  { key: 'approx', label: 'Aprox.' },
];

export interface CogsSummaryDto {
  total_cogs: number;
  units_sold: number;
  distinct_products_sold: number;
  /**
   * Sum (across products) of units that could not be matched to a layer.
   * Non-zero means either the backfill migration hasn't run yet, or
   * some products are over-sold vs the available layer history.
   * KEEP IN SYNC with backend ``CogsSummaryResponse.fallback_units_across_products``.
   */
  fallback_units_across_products: number;
}

/**
 * One layer-touched entry inside a product's COGS row.
 *
 * For ``method in (fifo, lifo)`` we get one entry per layer drained plus
 * an optional entry with ``source="fallback_layer_missing"`` when sold
 * > sum of open layers.
 *
 * For ``method=="approx"`` there is always exactly one entry with
 * ``source="approx_fallback"`` and ``layer_id=null``.
 */
export interface LayerBreakdownDto {
  /** ``null`` for fallback/approx rows (no real layer was touched). */
  layer_id: string | null;
  units_consumed: number;
  cost_per_unit: number;
  /** ``layer`` | ``approx_fallback`` | ``fallback_layer_missing`` */
  source: string;
}

/**
 * COGS per-product row. KEEP IN SYNC with ``CogsReportItemResponse``
 * in ``server/src/app/modules/partner/routes/hotel_products.py``.
 *
 * Intentionally omits ``id`` (Mongo ``_id``): the COGS aggregation joins
 * semantically on ``product_id`` (the stable cross-collection catalog
 * id), and emitting the aggregation's synthetic row id would either
 * be redundant or misleading. For drill-down by ObjectId, fetch the
 * catalog row via
 * ``hotel_products.find_one({product_id: row.product_id})`` client-side
 * or expose a dedicated endpoint.
 */
export interface CogsReportItemDto {
  product_id: string;
  name: string;
  category: string;
  units_sold: number;
  avg_unit_cost: number;
  cogs: number;
  /**
   * Per-layer consumption breakdown (Fase 6). Empty when ``method``
   * is unknown or no layers/fallback engaged (defensive default).
   */
  layer_breakdown: LayerBreakdownDto[];
}

export interface CogsReportDto {
  /** Echo of the requested method (fifo|lifo|approx). */
  method: CogsMethod;
  period: string;
  period_start: string;
  period_end: string;
  summary: CogsSummaryDto;
  items: CogsReportItemDto[];
}

// ─── Stock Value Report ──────────────────────────────────────────────────

export interface StockValueSummaryDto {
  total_stock_value: number;
  total_units: number;
  distinct_products: number;
}

export interface StockCategorySummaryDto {
  category: string;
  total_value: number;
  units: number;
  products: number;
}

export interface StockValueItemDto {
  id: string;
  product_id: string;
  name: string;
  category: string;
  quantity_available: number;
  cost_price: number;
  stock_value: number;
}

export interface StockValueReportDto {
  as_of: string;
  summary: StockValueSummaryDto;
  by_category: StockCategorySummaryDto[];
  items: StockValueItemDto[];
}

export type StockValueReportPeriod = 'month' | 'week' | 'year' | 'all';
