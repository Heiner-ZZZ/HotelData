import { isDevMode } from '@angular/core';

import { toast } from '../../../core/toast/toast.service';
import type { HotelSearchDto } from '../models/hotel-search.dto';
import type { HotelSearchFilters, HotelSearchPageData, HotelSearchResult } from '../models/hotel-search.model';

// [FIX BUG] Toast rate-limit so dev toasts don't stack on every page emit.
// `mapHotelSearchItems` re-fires on filter, sort and paginate (~9 emits per
// session). Without this cap, `toast()` queues fill the screen within 1
// minute. Console.error is NOT rate-limited — every drift still produces
// a log line. Only the visible toast is throttled.
let lastDriftToastAt = 0;
const DRIFT_TOAST_MIN_INTERVAL_MS = 6000;

/**
 * Dev-only toast helper that respects the rate-limit shared across ALL
 * audit paths in this file (driftEntries, altMissing, dto.items missing,
 * hasMismatch dropped-items). Each caller was previously firing a toast
 * on every emit; consolidating through this helper means a 6-second
 * minimum gap between ANY two toasts regardless of which audit fired.
 *
 * CROSS-AUDIT COUPLING: the rate-limit is SHARED across all four
 * callers above (driftEntries, altMissing, dto.items missing,
 * hasMismatch dropped-items). ANY caller blocks ANY subsequent toast
 * from any other caller for 6 seconds. This is intentional (no spam
 * across paginate / filter emits), so if a future reviewer asks "why
 * didn't the drift toast fire?" — the answer is probably "some OTHER
 * audit fired 3 seconds ago". Use per-category counters only if a
 * particular audit path needs independent visibility (none does
 * today).
 *
 * INIT: `lastDriftToastAt` starts at module-load = 0, so the very first
 * toast always fires immediately even if the caller is `dto.items
 * missing` (the earliest possible attempt). After that, every call
 * is gated by the 6-second rule.
 */
function safeToast(text: string, ms = 6000): void {
  if (isDevMode() && Date.now() - lastDriftToastAt > DRIFT_TOAST_MIN_INTERVAL_MS) {
    lastDriftToastAt = Date.now();
    toast(text, 'error', ms);
  }
}

export function mapHotelSearchItems(dto: HotelSearchDto): HotelSearchResult[] {
  // [FIX BUG] This mapper is the SINGLE CANONICAL audit point for the hotel
  // wire shape. It MUST be called by every consumer of `/api/hotels/search`
  // (see Wave A fix in `hotel-search-page.ts:effect`). Items missing canonical
  // fields are REJECTED here — NOT silently defaulted with `?? []` — so
  // downstream components can trust the canonical type and stop papering over
  // wire-shape drift with defensive guards. On the FIRST malformed item we
  // log loudly (`console.error`) and emit a dev-only toast so the regression
  // is visible in seconds, not after a guest reports it.
  // The `hasMismatch` flag is function-scoped intentionally: the mapper is
  // re-invoked on every page emit by the page's `effect()`, so exactly ONE
  // toast per emit is emitted. Don't hoist — that would mute warnings across
  // page changes.
  let hasMismatch = false;

  // Defence-in-depth: a Pydantic regression could drop the top-level
  // `items` array. Without this guard, `undefined.filter(...)` would crash
  // the page effect silently. Log + dev-toast the same way we do for
  // item-level drift so the regression is loud in dev and observable in prod.
  if (!Array.isArray(dto.items)) {
    // eslint-disable-next-line no-console
    console.error(
      '[hotel-search.mapper] HotelSearchDto response is missing the top-level '
        + '`items` array. Got:',
      dto,
    );
    safeToast(
      'HotelData: API wire-shape mismatch — `/api/hotels/search` response '
        + 'is missing the `items` array.',
    );
    return [];
  }

  const totalItems = dto.items.length;

  const validItems = dto.items
    // `prop_id > 0` rejects seed-data sentinels (id=0 was leaking into the
    // page and triggering same-image loremflickr + 400s on tracking).
    // `Array.isArray(item.destination_labels)` rejects seed-data that
    // bypassed the mapper envelope on the backend side.
    .filter((item) => {
      const isValid =
        item.prop_id != null &&
        item.prop_id > 0 &&
        Array.isArray(item.destination_labels);
      if (!isValid && !hasMismatch) {
        hasMismatch = true;
        // eslint-disable-next-line no-console
        console.error(
          '[hotel-search.mapper] API returned a hotel missing canonical '
            + 'fields (prop_id must be a positive int, destination_labels '
            + 'must be an array). First dropped item (sample):',
          item,
        );
        safeToast(
          'HotelData: API wire-shape mismatch — malformed hotels '
            + 'were dropped from this search.',
        );
      }
      return isValid;
    });

  // Surface the SCOPE of the drop, not just a sample. If 87 of 93 items were
  // malformed, one console.error with a sample is misleading; this makes it
  // obvious how many were dropped. The toast remains fire-once-per-page-load
  // to avoid UI spam.
  const dropped = totalItems - validItems.length;
  if (dropped > 0) {
    // eslint-disable-next-line no-console
    console.error(
      `[hotel-search.mapper] Dropped ${dropped} of ${totalItems} items `
        + 'on this page due to missing canonical fields.',
    );
  }

  // [FIX BUG] Per-field drift audit. The wire keys used below are the ones
  // the search endpoint is SUPPOSED to return for every item (`hotel_label`,
  // `hotel_display_label`, `prop_starrating`, `prop_review_score`, `min_price`,
  // `gross_revenue`, `gross_revenue_label`). If any of these vanish on a
  // backend regression, we surface SCOPE (count of missing items) instead of
  // silently substituting fallback strings — the user complained that
  // silent `?? []`/default-value swallows were hiding real wire-shape bugs.
  //
  // Items SURVIVE (no drop): losing 93k hotels from the page is worse than
  // visible drift. Synthesized fallbacks:
  //   - `name`: `Hotel ${prop_id}` when `hotel_label` is null/empty so the
  //     card's <h2> is never blank.
  //   - `minNightlyRateLabel`: derived from `min_price.toFixed(2)` since the
  //     wire has no `min_nightly_rate_label` key.
  //   - `imageUrl` / `matchedRoomType` / `availableRoomTypesCount`: `null` —
  //     card template handles null (gallery fallback for image, `;as rt`
  //     narrowing for room type, truthy `?.` for room count).
  // [FIX BUG] Two-bucket audit. `visible_*` keys are fields the canonical
  // HotelSearchResult depends on (card template reads them) — if any go
  // missing on the wire, items render with synthesized fallbacks and the
  // count is logged. `wire_only_*` keys are still on the wire but NOT
  // surfaced in HotelSearchResult because the analytics-fact semantics
  // (historical/cumulative) don't match the live-rate UI promise; we
  // still audit them so if the backend ever DROPS them entirely, we
  // notice — but a non-null wire value doesn't count as "missing" since
  // we deliberately null them out downstream. Two separate counters keep
  // the log signal clear: "users saw X bad cards" vs "wire silently
  // stopped returning something we'd wanted for future use".
  const audit = {
    visible_hotel_label: 0,
    visible_hotel_display_label: 0,
    visible_prop_starrating: 0,
    visible_prop_review_score: 0,
    wire_only_min_price: 0,
    wire_only_gross_revenue: 0,
    wire_only_gross_revenue_label: 0,
  };

  const mapped = validItems.map((item) => {
    if (item.hotel_label == null || item.hotel_label === '') audit.visible_hotel_label++;
    if (item.hotel_display_label == null || item.hotel_display_label === '') {
      audit.visible_hotel_display_label++;
    }
    if (item.prop_starrating == null) audit.visible_prop_starrating++;
    if (item.prop_review_score == null) audit.visible_prop_review_score++;
    if (item.min_price == null) audit.wire_only_min_price++;
    if (item.gross_revenue == null) audit.wire_only_gross_revenue++;
    if (item.gross_revenue_label == null || item.gross_revenue_label === '') {
      audit.wire_only_gross_revenue_label++;
    }
    return {
      id: item.prop_id!,
      name:
        typeof item.hotel_label === 'string' && item.hotel_label.length > 0
          ? item.hotel_label
          : `Hotel ${item.prop_id}`,
      displayName: item.hotel_display_label ?? '',
      stars: item.prop_starrating,
      reviewScore: item.prop_review_score,
      // Wire never provides `image_url` — the analytics-fact endpoint is
      // search-only. `card.ts:.imageUrl` already resolves to
      // `placeholderImageUrl(\`${id}1\`)` (loremflickr lock-by-prop_id)
      // when imageUrl is null and gallery is empty.
      imageUrl: null,
      destinationLabels: item.destination_labels,
      // Wire never provides `matched_room_type`; card template renders the
      // tag row conditionally with `@if (hotel().matchedRoomType; as rt)`.
      matchedRoomType: null,
      // [FIX BUG] Analytics-fact semantics don't match live-rate UI promise.
      // `min_price` is the historical smallest sale price (analytics-fact
      // row), `gross_revenue` is cumulative revenue across all bookings.
      // Surfacing either as "Desde $X" or "Total estimado $X" wrongly
      // implies live booking pricing, and guests who click "Ver
      // disponibilidad" will see a different number than the chip promised.
      // We DON'T fake-render them — card chip hides when canonical price
      // fields are null (`@if (hotel().minNightlyRate)` in card.html).
      // Live rates live on the hotel-detail page via a separate endpoint.
      minNightlyRate: null,
      minNightlyRateLabel: null,
      totalEstimated: null,
      totalEstimatedLabel: null,
      // Wire never provides `available_room_types_count`; card-summary
      // hall-effect-falsy check `h.availableRoomTypesCount ? ... : ''`
      // tolerates null.
      availableRoomTypesCount: null,
      selected: false,
    };
  });

  // Surface drift SCOPE (counts) only once per emit — mirror of the
  // existing `drop-summary` log + `altMissing` audit pattern, no new
  // noise mechanism. Cut the list at 3 fields in the toast so the user
  // gets actionable signal without UX-spam.
  const driftEntries = [
    audit.visible_hotel_label > 0 &&
      `${audit.visible_hotel_label}/${mapped.length} missing hotel_label`,
    audit.visible_hotel_display_label > 0 &&
      `${audit.visible_hotel_display_label}/${mapped.length} missing hotel_display_label`,
    audit.visible_prop_starrating > 0 &&
      `${audit.visible_prop_starrating}/${mapped.length} missing prop_starrating`,
    audit.visible_prop_review_score > 0 &&
      `${audit.visible_prop_review_score}/${mapped.length} missing prop_review_score`,
    audit.wire_only_min_price > 0 &&
      `${audit.wire_only_min_price}/${mapped.length} missing min_price (analytics-fact, not surfaced)`,
    audit.wire_only_gross_revenue > 0 &&
      `${audit.wire_only_gross_revenue}/${mapped.length} missing gross_revenue (analytics-fact, not surfaced)`,
    audit.wire_only_gross_revenue_label > 0 &&
      `${audit.wire_only_gross_revenue_label}/${mapped.length} missing gross_revenue_label (analytics-fact, not surfaced)`,
  ].filter(Boolean) as string[];

  if (driftEntries.length > 0) {
    // eslint-disable-next-line no-console
    console.error(
      '[hotel-search.mapper] Per-field drift on /api/hotels/search '
        + `(showing all ${mapped.length} items with synthesized fallbacks):`,
      driftEntries.join(' | '),
    );
    safeToast(
      `HotelData: ${driftEntries.length} field(s) drifted on /api/hotels/search — ${driftEntries.slice(0, 3).join(', ')}.`,
    );
  }

  return mapped;
}

export function mapHotelSearchResponse(dto: HotelSearchDto, filters: HotelSearchFilters): HotelSearchPageData {
  // [FIX BUG] Audit the response envelope's optional field too —
  // a missing `alternative_destinations` is a wire-shape regression,
  // not a default-empty case. Without this audit, a backend change that
  // drops the field would silently produce an empty suggestions list
  // with no visible evidence in dev or prod logs. Same pattern as
  // `mapHotelSearchItems`: console.error always (prod) + dev toast +
  // typed invariant enforced in `HotelSearchPageData` model.
  let altMissing = false;
  if (!Array.isArray(dto.alternative_destinations)) {
    altMissing = true;
    // eslint-disable-next-line no-console
    console.error(
      '[hotel-search.mapper] HotelSearchDto response is missing '
        + '`alternative_destinations` array. Got:',
      dto,
    );
    safeToast(
      'HotelData: API wire-shape mismatch — `/api/hotels/search` '
        + 'response is missing `alternative_destinations` array.',
    );
  }

  return {
    items: mapHotelSearchItems(dto),
    total: dto.total,
    page: dto.page,
    pageSize: dto.page_size,
    totalPages: dto.total_pages,
    hasPrev: dto.has_prev,
    hasNext: dto.has_next,
    filters,
    alternativeDestinations: altMissing
      ? []
      : // Array.isArray already passed above so the value IS an array;
        // the `!` is the typed mirror of that runtime invariant.
        // No `?? []` here — that would re-introduce the silent-swallow
        // pattern the user explicitly flagged out of this codebase.
        dto.alternative_destinations!.map((d) => ({
          id: d.id,
          displayName: d.display_name,
        })),
  };
}

export function createHotelSearchFilters(
  partial: Partial<HotelSearchFilters> = {}
): HotelSearchFilters {
  return {
    destination: partial.destination ?? '',
    checkIn: partial.checkIn ?? '',
    checkOut: partial.checkOut ?? '',
    adults: partial.adults ?? '1',
    children: partial.children ?? '0',
    rooms: partial.rooms ?? '1',
    minPrice: partial.minPrice ?? '',
    maxPrice: partial.maxPrice ?? '',
    minStars: partial.minStars ?? '',
    amenities: partial.amenities ?? [],
    amenitiesMode: partial.amenitiesMode ?? 'or',
    sortBy: partial.sortBy ?? 'price',
    compareIds: partial.compareIds ?? [],
    page: partial.page ?? 1,
  };
}
