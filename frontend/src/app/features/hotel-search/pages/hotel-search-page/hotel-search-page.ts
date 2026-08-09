import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, effect, inject, signal, untracked } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { getErrorStatus } from '../../../../shared/utils/http-error.util';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { FilterSidebarComponent } from '../../components/filter-sidebar/filter-sidebar';
import { HotelCardComponent } from '../../components/hotel-card/hotel-card';
import { SortControlComponent } from '../../components/sort-control/sort-control';
import { createHotelSearchFilters, mapHotelSearchResponse } from '../../mappers/hotel-search.mapper';
import type { HotelSearchDto } from '../../models/hotel-search.dto';
import type { AlternativeDestination, HotelSearchFilters, HotelSearchResult } from '../../models/hotel-search.model';

@Component({
  selector: 'app-hotel-search-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    FilterSidebarComponent,
    HotelCardComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    SortControlComponent,
    RouterLink,
  ],
  templateUrl: './hotel-search-page.html',
  styleUrl: './hotel-search-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HotelSearchPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly router = inject(Router);

  /** Reactive query-params bridge — toSignal keeps URL the source of truth. */
  private readonly qp = toSignal(this.activatedRoute.queryParamMap, {
    initialValue: this.activatedRoute.snapshot.queryParamMap,
  });

  readonly viewState = computed<ViewState>(() => {
    // error() ANTES de value(): value() lanza cuando el request falló.
    const err = this.searchResource.error();
    if (err) return getErrorStatus(err) === 404 ? 'empty' : 'error';
    const v = this.searchResource.value();
    if (this.searchResource.isLoading() && !v) return 'loading';
    return v?.items.length ? 'success' : 'empty';
  });

  // [FIX NG0600 cyclic dependency] Removed the `const data = this.searchResource.value()`
  // read entirely. `pageData` and `searchResource` formed a cycle: pageData
  // read `searchResource.value()` to check existence, and `searchResource`'s
  // URL formula read `pageData()` to build the request URL — Angular's reactive
  // graph produced the producerRecomputeValue → equal → value storm on every
  // emission. Flip-mode: filters are the SINGLE SOURCE OF TRUTH for the request,
  // derived purely from query params (`qp` is the URL state, `pageData` is its
  // typed view, the resource fires on that URL string).
  readonly pageData = computed<HotelSearchFilters>(() => {
    return createHotelSearchFilters({
      destination: this.qp().get('destination') ?? '',
      checkIn: this.qp().get('check_in') ?? '',
      checkOut: this.qp().get('check_out') ?? '',
      adults: this.qp().get('adults') ?? '1',
      children: this.qp().get('children') ?? '0',
      rooms: this.qp().get('rooms') ?? '1',
      minPrice: this.qp().get('price_min') ?? '',
      maxPrice: this.qp().get('price_max') ?? '',
      minStars: this.qp().get('star_rating') ?? '',
      amenities: (this.qp().get('amenities') ?? '').split(',').filter(Boolean),
      amenitiesMode: (this.qp().get('amenities_mode') as 'or' | 'and') ?? 'or',
      sortBy: (this.qp().get('sort_by') as 'price' | 'rating' | 'stars' | 'name') ?? 'price',
      page: Number(this.qp().get('page') ?? '1'),
      compareIds: (this.qp().get('compare_ids') || '').split(',').map(Number).filter((n) => !isNaN(n) && n > 0),
    });
  });

  /** httpResource — auto-fetches on URL change. Typed as `HotelSearchDto`
   *  so the mapper below receives the canonical shape without any cast
   *  (the prior `{ items: any[]; ... }` type silently hid wire-shape drift). */
  readonly searchResource = httpResource<HotelSearchDto>(() => {
    const f = this.pageData();
    return f ? `/api/hotels/availability?${this.toQueryString(f)}` : undefined;
  });

  /** Derived signals enumerated from search response. */
  readonly items = signal<HotelSearchResult[]>([]);
  readonly total = signal(0);
  readonly page = signal(1);
  readonly totalPages = signal(0);
  readonly totalIsEstimate = signal(false);
  readonly hasPrev = signal(false);
  readonly hasNext = signal(false);
  readonly showCompareMode = signal(false);
  readonly alternativeDestinations = signal<AlternativeDestination[]>([]);

  readonly currentFilters = computed(() => this.pageData());

  readonly selectedCompareIds = computed(() => {
    const fromUrl = this.currentFilters().compareIds;
    const fromItems = this.items().filter((h) => h.selected).map((h) => h.id);
    return [...new Set([...fromUrl, ...fromItems])];
  });

  constructor() {
    // Side-effect: derive from httpResource.value into the discrete signals that
    // the template reads. The id-gate prevents paged fetches from overwriting any
    // user's optimistic compare selections.
    effect(() => {
      // error() ANTES de value(): value() lanza cuando el request falló (ej. 403).
      if (this.searchResource.error()) return;
      const data = this.searchResource.value();
      if (!data) return;
      const currentFilters = this.pageData();
      const fromCompareIds = new Set(currentFilters?.compareIds ?? []);
      // [FIX] `untracked()` around `selectedCompareIds()` breaks the NG0600
      // self-write re-entrancy: `selectedCompareIds` is a computed that
      // transitively reads `this.items()`, so calling it inside this effect
      // would subscribe us to `items`. Then `this.items.set(...)` further
      // down would trigger `producerRecomputeValue → equal → value` on every
      // emission. We just need the pre-write selected IDs to merge into the
      // new page — untracking that one read is the minimum diff.
      const selected = new Set(untracked(() => this.selectedCompareIds()));
      // [FIX BUG] Use `mapHotelSearchResponse` so the response envelope
      // (`total_pages` → `totalPages`, `has_prev` → `hasPrev`, `alternative_
      // destinations` → `alternativeDestinations`, plus the per-item mapping
      // via `mapHotelSearchItems`) goes through the SAME canonical mapper
      // — never access `data.X` directly here. The mapper is the audit point
      // for wire-shape drift; bypassing it (Page → data.X) reintroduces the
      // silent-fallback class of bugs the user asked us to stop.
      const page = mapHotelSearchResponse(data, currentFilters);
      this.items.set(
        page.items.map((h) => ({
          ...h,
          selected: selected.has(h.id) || fromCompareIds.has(h.id),
        })),
      );
      this.total.set(page.total);
      this.page.set(page.page);
      this.totalPages.set(page.totalPages);
      this.totalIsEstimate.set(page.totalIsEstimate);
      this.hasPrev.set(page.hasPrev);
      this.hasNext.set(page.hasNext);
      this.alternativeDestinations.set(page.alternativeDestinations);
      this.showCompareMode.set(page.filters.compareIds.length > 0);
    }, { allowSignalWrites: true });
  }

  updateFilters(filters: HotelSearchFilters) {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: this.toQueryParams(filters),
    });
  }

  goToPage(page: number) {
    const filters = this.currentFilters();
    this.updateFilters({ ...filters, page });
  }

  /** Botón "Elegir fechas" de una card: lleva el foco al calendario del
   *  filtro (check-in) y abre el picker nativo — el total de la card se
   *  recalcula al aplicar el rango (patrón Expedia: fechas primero). */
  onChooseDates() {
    const input = document.querySelector<HTMLInputElement>(
      '.filter-sidebar input[formControlName="checkIn"]',
    );
    if (!input) return;
    input.scrollIntoView({ behavior: 'smooth', block: 'center' });
    if (typeof input.showPicker === 'function') {
      input.showPicker();
    } else {
      input.focus({ preventScroll: true });
    }
  }

  onCompareSelected(hotelId: number) {
    const current = this.selectedCompareIds();
    let next: number[];
    if (current.includes(hotelId)) {
      next = current.filter((id) => id !== hotelId);
    } else if (current.length >= 3) {
      return; // Max 3 hotels
    } else {
      next = [...current, hotelId];
    }
    // Update items selection state
    this.items.update((items) =>
      items.map((h) => ({ ...h, selected: next.includes(h.id) }))
    );
    this.showCompareMode.set(next.length > 0);
    // Sync compare IDs to URL so navigation preserves state
    const filters = this.currentFilters();
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { ...this.toQueryParams(filters), compare_ids: next.length ? next.join(',') : null },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  clearCompare() {
    this.items.update((items) =>
      items.map((h) => ({ ...h, selected: false }))
    );
    this.showCompareMode.set(false);
    // Clear compare_ids from URL
    const filters = this.currentFilters();
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { ...this.toQueryParams(filters), compare_ids: null },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  /** Flatten the filter object into a URLSearchParams query string for the
   *  httpResource request. Same null-skip semantics as the router call. */
  private toQueryString(filters: HotelSearchFilters): string {
    const sp = new URLSearchParams();
    // The guest search is intentionally paged in small batches. Keep this
    // explicit so a backend default change cannot make the first request
    // expensive or render more than the promised 10 cards.
    sp.set('page_size', '10');
    if (filters.destination) sp.set('destination', filters.destination);
    if (filters.checkIn) sp.set('check_in', filters.checkIn);
    if (filters.checkOut) sp.set('check_out', filters.checkOut);
    if (filters.adults !== '1') sp.set('adults', filters.adults);
    if (filters.children !== '0') sp.set('children', filters.children);
    if (filters.rooms !== '1') sp.set('rooms', filters.rooms);
    if (filters.minPrice) sp.set('price_min', filters.minPrice);
    if (filters.maxPrice) sp.set('price_max', filters.maxPrice);
    if (filters.minStars) sp.set('star_rating', filters.minStars);
    if (filters.amenities.length) sp.set('amenities', filters.amenities.join(','));
    if (filters.amenitiesMode !== 'or') sp.set('amenities_mode', filters.amenitiesMode);
    if (filters.sortBy !== 'price') sp.set('sort_by', filters.sortBy);
    if (filters.compareIds.length) sp.set('compare_ids', filters.compareIds.join(','));
    if (filters.page > 1) sp.set('page', String(filters.page));
    return sp.toString();
  }

  /** Build a `Record<string, string | number | null>` for `router.navigate`
   *  calls. `null` values are deleted from the URL by the router (the same
   *  null-skip behaviour as `toQueryString`). Defaults that match the page's
   *  initial state are returned as `null` so the URL stays clean. */
  private toQueryParams(filters: HotelSearchFilters): Record<string, string | number | null> {
    return {
      destination: filters.destination || null,
      check_in: filters.checkIn || null,
      check_out: filters.checkOut || null,
      adults: filters.adults !== '1' ? filters.adults : null,
      children: filters.children !== '0' ? filters.children : null,
      rooms: filters.rooms !== '1' ? filters.rooms : null,
      price_min: filters.minPrice || null,
      price_max: filters.maxPrice || null,
      star_rating: filters.minStars || null,
      amenities: filters.amenities.length ? filters.amenities.join(',') : null,
      amenities_mode: filters.amenitiesMode !== 'or' ? filters.amenitiesMode : null,
      sort_by: filters.sortBy !== 'price' ? filters.sortBy : null,
      page: filters.page > 1 ? filters.page : null,
    };
  }
}
