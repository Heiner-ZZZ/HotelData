import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { FilterSidebarComponent } from '../../components/filter-sidebar/filter-sidebar';
import { HotelCardComponent } from '../../components/hotel-card/hotel-card';
import { SortControlComponent } from '../../components/sort-control/sort-control';
import { createHotelSearchFilters } from '../../mappers/hotel-search.mapper';
import type { AlternativeDestination, HotelSearchFilters, HotelSearchResult } from '../../models/hotel-search.model';
import { HotelSearchApiService } from '../../services/hotel-search-api.service';

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
  private readonly destroyRef = inject(DestroyRef);
  private readonly hotelSearchApi = inject(HotelSearchApiService);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly pageData = signal<HotelSearchFilters | null>(null);
  readonly items = signal<HotelSearchResult[]>([]);
  readonly total = signal(0);
  readonly page = signal(1);
  readonly totalPages = signal(0);
  readonly hasPrev = signal(false);
  readonly hasNext = signal(false);
  readonly showCompareMode = signal(false);
  readonly alternativeDestinations = signal<AlternativeDestination[]>([]);

  readonly currentFilters = computed(() => {
    const data = this.pageData();
    if (data) return data;
    return createHotelSearchFilters();
  });

  readonly selectedCompareIds = computed(() =>
    this.items().filter((h) => h.selected).map((h) => h.id)
  );

  constructor() {
    this.activatedRoute.queryParamMap
      .pipe(
        map((queryParams) =>
          createHotelSearchFilters({
            destination: queryParams.get('destination') ?? '',
            checkIn: queryParams.get('check_in') ?? '',
            checkOut: queryParams.get('check_out') ?? '',
            adults: queryParams.get('adults') ?? '1',
            children: queryParams.get('children') ?? '0',
            rooms: queryParams.get('rooms') ?? '1',
            minPrice: queryParams.get('price_min') ?? '',
            maxPrice: queryParams.get('price_max') ?? '',
            minStars: queryParams.get('star_rating') ?? '',
            amenities: queryParams.get('amenities') ?? '',
            amenitiesMode: (queryParams.get('amenities_mode') as 'or' | 'and') ?? 'or',
            sortBy: (queryParams.get('sort_by') as 'price' | 'rating' | 'stars' | 'name') ?? 'price',
            page: Number(queryParams.get('page') ?? '1'),
            compareIds: (queryParams.get('compare_ids') || '').split(',').map(Number).filter((n) => !isNaN(n) && n > 0),
          })
        ),
        distinctUntilChanged((previous, current) => JSON.stringify(previous) === JSON.stringify(current)),
        switchMap((filters) => {
          this.viewState.set('loading');
          this.pageData.set(filters);
          this.showCompareMode.set(filters.compareIds.length > 0);
          return this.hotelSearchApi.search(filters);
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (pageData) => {
          // Preserve selection state when items refresh
          const selected = new Set(this.selectedCompareIds());
          const items = pageData.items.map((h) => ({
            ...h,
            selected: selected.has(h.id),
          }));
          this.items.set(items);
          this.total.set(pageData.total);
          this.page.set(pageData.page);
          this.totalPages.set(pageData.totalPages);
          this.hasPrev.set(pageData.hasPrev);
          this.hasNext.set(pageData.hasNext);
          this.alternativeDestinations.set(pageData.alternativeDestinations ?? []);
          this.viewState.set(items.length ? 'success' : 'empty');
        },
        error: () => {
          this.viewState.set('error');
        }
      });
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
  }

  clearCompare() {
    this.items.update((items) =>
      items.map((h) => ({ ...h, selected: false }))
    );
    this.showCompareMode.set(false);
  }

  private toQueryParams(filters: HotelSearchFilters) {
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
      amenities: filters.amenities || null,
      amenities_mode: filters.amenitiesMode !== 'or' ? filters.amenitiesMode : null,
      sort_by: filters.sortBy !== 'price' ? filters.sortBy : null,
      compare_ids: filters.compareIds.length ? filters.compareIds.join(',') : null,
      page: filters.page > 1 ? filters.page : null,
    };
  }
}
