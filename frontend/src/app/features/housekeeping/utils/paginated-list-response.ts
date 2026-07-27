import type { PaginatedResponse } from '../services/housekeeping-api.service';

/**
 * Template-friendly paginated response — accepted by housekeeping + maintenance
 * pages.
 *
 * Mirrors the backend's `PaginatedResponse<T>` keys (`items`, `total`, `page`,
 * `totalPages`, `hasPrev`, `hasNext`). All fields except `items` are optional
 * so a partial / null-island response still type-checks at consumer sites
 * (covers 204 No Content, middleware sparse responses, and rxjs stream
 * pre-load states).
 *
 * NOTE: a previous version of this interface exposed a `pages?: number` alias;
 * that field was removed because the backend's `PaginatedResponse<T>` provides
 * `totalPages` directly and never exposes a `pages` key. Templates read
 * `totalPages/hasPrev/hasNext` — they don't need a separate alias.
 */
export interface PaginatedListResponse<T> {
  items: T[];
  total?: number;
  page?: number;
  totalPages?: number;
  hasPrev?: boolean;
  hasNext?: boolean;
}

/**
 * Normalize a backend `PaginatedResponse<T> | null | undefined` into the
 * template-friendly `PaginatedListResponse<T>`.
 *
 * Why a dedicated helper: housekeeping + maintenance pages used to inline the
 * same `{ items: r?.items ?? [], totalPages: r?.pages ?? 1, ... }` block —
 * the duplication was a maintenance hazard (one drifted from the other and a
 * pagination flag went stale). Extracted here so both pages share the
 * canonical normalization rules.
 *
 * Implementation notes:
 * - Source `totalPages / hasPrev / hasNext` straight from the backend payload
 *   (those fields are required on `PaginatedResponse<T>`). Falls back to
 *   computed values only when the payload is null-ish.
 * - Keeps a defensive `?? 1` floor on `totalPages` so the pagination UI never
 *   renders "0 of 0" under a sparse middleware response.
 * - `never[]` from the empty `items` literal widens to `T[]` via covariance,
 *   so callers can write `of<PaginatedListResponse<X>>({ items: [] })` without
 *   casts.
 */
export function normalizePaginatedList<T>(
  r: PaginatedResponse<T> | null | undefined,
): PaginatedListResponse<T> {
  const items = r?.items ?? [];
  const page = r?.page ?? 1;
  const totalPages = r?.totalPages ?? 1;
  return {
    items,
    total: r?.total,
    page,
    totalPages,
    hasPrev: r?.hasPrev ?? page > 1,
    hasNext: r?.hasNext ?? page < totalPages,
  };
}
