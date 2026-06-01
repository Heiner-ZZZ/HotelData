import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { FilterSidebarComponent } from '../../components/filter-sidebar/filter-sidebar';
import { HotelCardComponent } from '../../components/hotel-card/hotel-card';
import { SortControlComponent } from '../../components/sort-control/sort-control';
import type { HotelSearchFilters, HotelSearchViewModel } from '../../models/hotel-search.model';
import { HotelSearchApiService } from '../../services/hotel-search-api.service';

@Component({
  selector: 'app-hotel-search-page',
  standalone: true,
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    FilterSidebarComponent,
    HotelCardComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    ReactiveFormsModule,
    SortControlComponent
  ],
  templateUrl: './hotel-search-page.html',
  styleUrl: './hotel-search-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HotelSearchPageComponent {
  private readonly formBuilder = inject(FormBuilder);
  private readonly hotelSearchApi = inject(HotelSearchApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<HotelSearchViewModel | null>(null);

  readonly filtersForm = this.formBuilder.nonNullable.group({
    destination: '',
    minPrice: '',
    maxPrice: '',
    minStars: '',
    promotion: '',
    adults: '',
    children: '',
    rooms: ''
  });

  readonly resultsSummary = computed(() => {
    const vm = this.viewModel();
    if (!vm) {
      return 'Cargando resultados...';
    }

    const rangeText =
      vm.total > 0 ? `${vm.startIndex}-${vm.endIndex} de ${vm.total}` : '0 resultados';
    return `${rangeText} · Pagina ${vm.page} de ${vm.totalPages || 1} · Fuente ${vm.sourceCollection}`;
  });

  constructor() {
    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const filters: HotelSearchFilters = {
        destination: params.get('destination') ?? '',
        minPrice: params.get('min_price') ?? '',
        maxPrice: params.get('max_price') ?? '',
        minStars: params.get('min_stars') ?? '',
        promotion: params.get('promotion') ?? '',
        adults: params.get('adults') ?? '',
        children: params.get('children') ?? '',
        rooms: params.get('rooms') ?? ''
      };
      const page = Number(params.get('page') ?? '1') || 1;

      this.filtersForm.patchValue(filters, { emitEvent: false });
      this.loadSearch(filters, page);
    });
  }

  onSubmit() {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: this.toQueryParams(this.filtersForm.getRawValue(), 1)
    });
  }

  onReset() {
    this.filtersForm.reset({
      destination: '',
      minPrice: '',
      maxPrice: '',
      minStars: '',
      promotion: '',
      adults: '',
      children: '',
      rooms: ''
    });
    void this.router.navigate(['/search']);
  }

  goToPage(page: number) {
    if (page < 1) {
      return;
    }

    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: this.toQueryParams(this.filtersForm.getRawValue(), page)
    });
  }

  trackByHotelId = (_index: number, hotel: { id: number }) => hotel.id;

  private loadSearch(filters: HotelSearchFilters, page: number) {
    this.viewState.set('loading');

    this.hotelSearchApi
      .searchHotels(filters, page)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (viewModel) => {
          this.viewModel.set(viewModel);
          this.viewState.set(viewModel.items.length ? 'success' : 'empty');
        },
        error: () => {
          this.viewModel.set(null);
          this.viewState.set('error');
        }
      });
  }

  private toQueryParams(filters: HotelSearchFilters, page: number) {
    return {
      destination: filters.destination || null,
      min_price: filters.minPrice || null,
      max_price: filters.maxPrice || null,
      min_stars: filters.minStars || null,
      promotion: filters.promotion || null,
      adults: filters.adults || null,
      children: filters.children || null,
      rooms: filters.rooms || null,
      page: page > 1 ? page : null
    };
  }
}
