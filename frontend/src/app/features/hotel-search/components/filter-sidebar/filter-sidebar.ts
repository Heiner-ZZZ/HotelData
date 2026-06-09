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
    minPrice: [''],
    maxPrice: [''],
    minStars: [''],
    promotion: ['' as HotelSearchFilters['promotion']],
    adults: [''],
    children: [''],
    rooms: ['']
  });

  constructor() {
    effect(() => {
      const filters = this.filters();
      this.form.patchValue(
        {
          destination: filters.destination,
          minPrice: filters.minPrice,
          maxPrice: filters.maxPrice,
          minStars: filters.minStars,
          promotion: filters.promotion,
          adults: filters.adults,
          children: filters.children,
          rooms: filters.rooms
        },
        { emitEvent: false }
      );
    });
  }

  applyFilters() {
    this.submitted.emit({
      ...this.filters(),
      ...this.form.getRawValue(),
      page: 1
    });
  }

  resetFilters() {
    this.form.reset({
      destination: '',
      minPrice: '',
      maxPrice: '',
      minStars: '',
      promotion: '',
      adults: '',
      children: '',
      rooms: ''
    });
    this.applyFilters();
  }
}
