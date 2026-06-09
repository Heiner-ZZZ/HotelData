import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { FilterSidebarComponent } from '../../components/filter-sidebar/filter-sidebar';
import { HotelCardComponent } from '../../components/hotel-card/hotel-card';
import { SortControlComponent } from '../../components/sort-control/sort-control';
import { createHotelSearchFilters } from '../../mappers/hotel-search.mapper';
import type { HotelSearchFilters, HotelSearchPageData } from '../../models/hotel-search.model';
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
    SortControlComponent
  ],
  templateUrl: './hotel-search-page.html',
  styleUrl: './hotel-search-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HotelSearchPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly authService = inject(AuthService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly hotelSearchApi = inject(HotelSearchApiService);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly pageData = signal<HotelSearchPageData | null>(null);
  readonly currentFilters = computed(() => this.pageData()?.filters ?? createHotelSearchFilters());
  readonly pageHeader = computed(() => {
    const role = this.authService.currentUser()?.primaryRole;

    if (!role || role === 'cliente') {
      return {
        eyebrow: 'Cliente / viajero',
        title: 'Buscar hoteles',
        description: 'Exploración tipo marketplace sobre datos analíticos reales. No crea reservas ni procesa pagos.'
      };
    }

    return {
      eyebrow: 'Exploración / referencia',
      title: 'Buscar hoteles',
      description: 'Vista pública de referencia para validar contenido, fichas, precios y experiencia comercial sin salir del panel operativo.'
    };
  });

  constructor() {
    this.activatedRoute.queryParamMap
      .pipe(
        map((queryParams) =>
          createHotelSearchFilters({
            destination: queryParams.get('destination') ?? '',
            minPrice: queryParams.get('min_price') ?? '',
            maxPrice: queryParams.get('max_price') ?? '',
            minStars: queryParams.get('min_stars') ?? '',
            promotion: ((queryParams.get('promotion') ?? '') as HotelSearchFilters['promotion']) || '',
            adults: queryParams.get('adults') ?? '',
            children: queryParams.get('children') ?? '',
            rooms: queryParams.get('rooms') ?? '',
            page: Number(queryParams.get('page') ?? '1')
          })
        ),
        distinctUntilChanged((previous, current) => JSON.stringify(previous) === JSON.stringify(current)),
        switchMap((filters) => {
          this.viewState.set('loading');
          return this.hotelSearchApi.search(filters);
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (pageData) => {
          this.pageData.set(pageData);
          this.viewState.set(pageData.items.length ? 'success' : 'empty');
        },
        error: () => {
          this.viewState.set('error');
        }
      });
  }

  updateFilters(filters: HotelSearchFilters) {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: this.toQueryParams(filters)
    });
  }

  goToPage(page: number) {
    const filters = this.currentFilters();
    this.updateFilters({
      ...filters,
      page
    });
  }

  private toQueryParams(filters: HotelSearchFilters) {
    return {
      destination: filters.destination || null,
      min_price: filters.minPrice || null,
      max_price: filters.maxPrice || null,
      min_stars: filters.minStars || null,
      promotion: filters.promotion || null,
      adults: filters.adults || null,
      children: filters.children || null,
      rooms: filters.rooms || null,
      page: filters.page > 1 ? filters.page : null
    };
  }
}
