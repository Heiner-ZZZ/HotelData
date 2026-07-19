import { ChangeDetectionStrategy, Component, effect, input, output } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import type { HotelSearchFilters } from '../../models/hotel-search.model';

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
    destination: [''],
    checkIn: [''],
    checkOut: [''],
    adults: ['1'],
    children: ['0'],
    rooms: ['1'],
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
          destination: filters.destination,
          checkIn: filters.checkIn,
          checkOut: filters.checkOut,
          adults: filters.adults,
          children: filters.children,
          rooms: filters.rooms,
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
      destination: raw.destination,
      checkIn: raw.checkIn,
      checkOut: raw.checkOut,
      adults: raw.adults,
      children: raw.children,
      rooms: raw.rooms,
      minPrice: raw.minPrice,
      maxPrice: raw.maxPrice,
      minStars: raw.minStars,
      amenities: amenitiesStr ? amenitiesStr.split(',').map(a => a.trim()).filter(Boolean) : [],
      amenitiesMode: raw.amenitiesMode,
      sortBy: raw.sortBy,
      page: 1,
      compareIds: this.filters().compareIds,
    });
  }

  resetFilters() {
    this.form.reset({
      destination: '',
      checkIn: '',
      checkOut: '',
      adults: '1',
      children: '0',
      rooms: '1',
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
