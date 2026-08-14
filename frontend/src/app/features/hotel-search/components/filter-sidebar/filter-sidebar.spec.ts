import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';

import { DestinationAutocompleteComponent } from '../../../../shared/ui/destination-autocomplete/destination-autocomplete';
import { FilterSidebarComponent } from './filter-sidebar';
import type { HotelSearchFilters } from '../../models/hotel-search.model';

function makeFilters(overrides: Partial<HotelSearchFilters> = {}): HotelSearchFilters {
  return {
    destination: '',
    checkIn: '',
    checkOut: '',
    adults: '1',
    children: '0',
    rooms: '1',
    minPrice: '',
    maxPrice: '',
    minStars: '',
    amenities: [],
    amenitiesMode: 'or',
    sortBy: 'price',
    compareIds: [],
    page: 1,
    ...overrides,
  };
}

describe('FilterSidebarComponent — refinamientos (destino/fechas/huéspedes viven en el booking-bar superior)', () => {
  function setup(filters = makeFilters()) {
    TestBed.configureTestingModule({
      imports: [FilterSidebarComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const fixture = TestBed.createComponent(FilterSidebarComponent);
    const comp = fixture.componentInstance;
    fixture.componentRef.setInput('filters', filters);
    fixture.detectChanges();
    return { fixture, comp };
  }

  it('NO renderiza los campos que ahora viven en el booking-bar (destino, fechas, huéspedes, título)', () => {
    const { fixture } = setup();
    expect(fixture.nativeElement.querySelector('h2')).toBeNull();
    expect(fixture.debugElement.query(By.directive(DestinationAutocompleteComponent))).toBeNull();
    expect(fixture.nativeElement.querySelector('input[formControlName="checkIn"]')).toBeNull();
    expect(fixture.nativeElement.querySelector('input[formControlName="checkOut"]')).toBeNull();
    expect(fixture.nativeElement.querySelector('input[formControlName="adults"]')).toBeNull();
    expect(fixture.nativeElement.querySelector('input[formControlName="children"]')).toBeNull();
    expect(fixture.nativeElement.querySelector('input[formControlName="rooms"]')).toBeNull();
  });

  it('renderiza los refinamientos: precio, estrellas, amenities y orden', () => {
    const { fixture } = setup();
    expect(fixture.nativeElement.querySelector('input[formControlName="minPrice"]')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('input[formControlName="maxPrice"]')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('input[formControlName="minStars"]')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('input[formControlName="amenities"]')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('select[formControlName="sortBy"]')).toBeTruthy();
  });

  it('applyFilters conserva destino/fechas/huéspedes del estado externo y emite los refinamientos', () => {
    const { fixture, comp } = setup(
      makeFilters({ destination: 'Quito', checkIn: '2026-09-01', checkOut: '2026-09-03', adults: '2', children: '1', rooms: '2' }),
    );
    let submitted: HotelSearchFilters | null = null;
    comp.submitted.subscribe((f) => (submitted = f));

    comp.form.controls.minPrice.setValue('50');
    comp.form.controls.maxPrice.setValue('200');
    comp.form.controls.minStars.setValue('4');
    comp.form.controls.amenities.setValue('wifi, piscina');
    comp.form.controls.amenitiesMode.setValue('and');
    comp.form.controls.sortBy.setValue('rating');
    comp.applyFilters();

    expect(submitted).toMatchObject({
      destination: 'Quito',
      checkIn: '2026-09-01',
      checkOut: '2026-09-03',
      adults: '2',
      children: '1',
      rooms: '2',
      minPrice: '50',
      maxPrice: '200',
      minStars: '4',
      amenities: ['wifi', 'piscina'],
      amenitiesMode: 'and',
      sortBy: 'rating',
      page: 1,
    });
  });

  it('reset limpia solo los refinamientos y conserva destino/fechas/huéspedes', () => {
    const { fixture, comp } = setup(
      makeFilters({ destination: 'Quito', checkIn: '2026-09-01', checkOut: '2026-09-03', adults: '2' }),
    );
    let submitted: HotelSearchFilters | null = null;
    comp.submitted.subscribe((f) => (submitted = f));

    comp.form.controls.minPrice.setValue('50');
    comp.form.controls.minStars.setValue('4');
    comp.resetFilters();

    expect(submitted).toMatchObject({
      destination: 'Quito',
      checkIn: '2026-09-01',
      checkOut: '2026-09-03',
      adults: '2',
      minPrice: '',
      maxPrice: '',
      minStars: '',
      amenities: [],
      amenitiesMode: 'or',
      sortBy: 'price',
    });
  });

  it('sincroniza los refinamientos desde los filtros externos al montar', () => {
    const { fixture } = setup(
      makeFilters({ minPrice: '30', maxPrice: '300', minStars: '3', amenities: ['wifi'], amenitiesMode: 'and', sortBy: 'name' }),
    );
    expect(compFormValue(fixture, 'minPrice')).toBe('30');
    expect(compFormValue(fixture, 'maxPrice')).toBe('300');
    expect(compFormValue(fixture, 'minStars')).toBe('3');
    expect(compFormValue(fixture, 'amenities')).toBe('wifi');
    expect(compFormValue(fixture, 'amenitiesMode')).toBe('and');
    expect(compFormValue(fixture, 'sortBy')).toBe('name');
  });
});

function compFormValue(fixture: any, control: string): string {
  return (fixture.componentInstance as FilterSidebarComponent).form.controls[
    control as 'minPrice' | 'maxPrice' | 'minStars' | 'amenities' | 'amenitiesMode' | 'sortBy'
  ].value;
}
