import { ChangeDetectionStrategy, Component, effect, input, output } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import type { HotelSearchFilters } from '../../models/hotel-search.model';

/**
 * Refinamientos de la búsqueda (precio, estrellas, amenities, orden).
 * Destino / fechas / huéspedes viven en el booking-bar superior compartido
 * (app-booking-search-bar) — este panel solo emite los refinamientos y
 * conserva el resto del estado de los filtros externos.
 */
@Component({
  selector: 'app-filter-sidebar',
  imports: [ReactiveFormsModule],
  templateUrl: './filter-sidebar.html',
  styleUrl: './filter-sidebar.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FilterSidebarComponent {
  readonly filters = input.required<HotelSearchFilters>();
  readonly submitted = output<HotelSearchFilters>();

  private readonly formBuilder = new FormBuilder();

  readonly form = this.formBuilder.nonNullable.group({
    minPrice: [''],
    maxPrice: [''],
    minStars: [''],
    amenities: [''],
    amenitiesMode: ['or' as HotelSearchFilters['amenitiesMode']],
    sortBy: ['price' as HotelSearchFilters['sortBy']],
  });

  constructor() {
    effect(() => {
      const filters = this.filters();
      this.form.patchValue(
        {
          minPrice: filters.minPrice,
          maxPrice: filters.maxPrice,
          minStars: filters.minStars,
          amenities: Array.isArray(filters.amenities) ? filters.amenities.join(', ') : filters.amenities,
          amenitiesMode: filters.amenitiesMode,
          sortBy: filters.sortBy,
        },
        { emitEvent: false }
      );
    });
  }

  applyFilters() {
    const raw = this.form.getRawValue();
    const amenitiesStr = (raw.amenities || '').trim();
    this.submitted.emit({
      ...this.filters(),
      minPrice: raw.minPrice,
      maxPrice: raw.maxPrice,
      minStars: raw.minStars,
      amenities: amenitiesStr ? amenitiesStr.split(',').map(a => a.trim()).filter(Boolean) : [],
      amenitiesMode: raw.amenitiesMode,
      sortBy: raw.sortBy,
      page: 1,
    });
  }

  resetFilters() {
    this.form.reset({
      minPrice: '',
      maxPrice: '',
      minStars: '',
      amenities: '',
      amenitiesMode: 'or',
      sortBy: 'price',
    });
    this.applyFilters();
  }
}
