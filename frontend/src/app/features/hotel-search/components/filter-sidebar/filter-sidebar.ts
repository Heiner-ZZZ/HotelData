import { Component, effect, input, output } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import type { HotelSearchFilters } from '../../models/hotel-search.model';

@Component({
  selector: 'app-filter-sidebar',
  imports: [ReactiveFormsModule],
  templateUrl: './filter-sidebar.html',
  styleUrl: './filter-sidebar.scss'
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
          amenities: filters.amenities,
          amenitiesMode: filters.amenitiesMode,
          sortBy: filters.sortBy,
        },
        { emitEvent: false }
      );
    });
  }

  applyFilters() {
    this.submitted.emit({
      ...this.filters(),
      ...this.form.getRawValue(),
      page: 1,
      compareIds: this.filters().compareIds,
    } as HotelSearchFilters);
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
