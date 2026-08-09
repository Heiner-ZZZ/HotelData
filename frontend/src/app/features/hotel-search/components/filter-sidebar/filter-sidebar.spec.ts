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

describe('FilterSidebarComponent — destino con autocomplete compartido', () => {
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

  function autocomplete(fixture: ReturnType<typeof setup>['fixture']) {
    return fixture.debugElement
      .query(By.directive(DestinationAutocompleteComponent))
      .componentInstance as DestinationAutocompleteComponent;
  }

  function daInput(fixture: ReturnType<typeof setup>['fixture']) {
    return fixture.nativeElement.querySelector('.da-input') as HTMLInputElement;
  }

  it('renders el autocomplete compartido en el campo Destino (sin input nativo)', () => {
    const { fixture } = setup();
    expect(fixture.debugElement.query(By.css('app-destination-autocomplete'))).toBeTruthy();
    expect(fixture.nativeElement.querySelector('input[formControlName="destination"]')).toBeNull();
    expect(daInput(fixture)).toBeTruthy();
  });

  it('muestra el destino externo en el input del autocomplete al montar', () => {
    const { fixture } = setup(makeFilters({ destination: 'Quito' }));
    expect(daInput(fixture).value).toBe('Quito');
  });

  it('sincroniza el input cuando los filtros cambian después del montaje', () => {
    const { fixture } = setup(makeFilters({ destination: 'Lima' }));
    fixture.componentRef.setInput('filters', makeFilters({ destination: 'Hotel Lima Centro' }));
    fixture.detectChanges();
    expect(daInput(fixture).value).toBe('Hotel Lima Centro');
  });

  it('escribir en el autocomplete actualiza el form y los filtros emitidos', () => {
    const { fixture, comp } = setup();
    let submitted: HotelSearchFilters | null = null;
    comp.submitted.subscribe((f) => (submitted = f));

    const input = daInput(fixture);
    input.value = 'Madrid';
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    expect(comp.form.controls.destination.value).toBe('Madrid');

    comp.applyFilters();
    expect(submitted?.destination).toBe('Madrid');
  });

  it('elegir una sugerencia llena el input y se propaga al form', () => {
    const { fixture, comp } = setup();
    let submitted: HotelSearchFilters | null = null;
    comp.submitted.subscribe((f) => (submitted = f));

    const ac = autocomplete(fixture);
    ac.suggestions.set([{ id: 7, name: 'Hotel Lima Centro', type: 'hotel' }]);
    ac.dropdownOpen.set(true);
    ac.choose({ id: 7, name: 'Hotel Lima Centro', type: 'hotel' });
    fixture.detectChanges();

    expect(daInput(fixture).value).toBe('Hotel Lima Centro');
    expect(comp.form.controls.destination.value).toBe('Hotel Lima Centro');

    comp.applyFilters();
    expect(submitted?.destination).toBe('Hotel Lima Centro');
  });

  it('reset limpia el destino y lo refleja en el autocomplete', () => {
    const { fixture, comp } = setup(makeFilters({ destination: 'Quito' }));
    fixture.detectChanges();
    comp.resetFilters();
    fixture.detectChanges();
    expect(comp.form.controls.destination.value).toBe('');
    expect(daInput(fixture).value).toBe('');
  });
});

describe('FilterSidebarComponent — calendario solo fechas futuras/presentes', () => {
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

  it('check-in y check-out no permiten fechas pasadas (min = hoy)', () => {
    const { fixture } = setup();
    const checkIn = fixture.nativeElement.querySelector('input[formControlName="checkIn"]') as HTMLInputElement;
    const checkOut = fixture.nativeElement.querySelector('input[formControlName="checkOut"]') as HTMLInputElement;
    const today = new Date().toLocaleDateString('sv-SE');
    expect(checkIn.min).toBe(today);
    expect(checkOut.min).toBe(today);
  });

  it('check-out no puede ser anterior al check-in elegido', () => {
    const { fixture, comp } = setup();
    comp.form.controls.checkIn.setValue('2026-09-01');
    fixture.detectChanges();
    const checkOut = fixture.nativeElement.querySelector('input[formControlName="checkOut"]') as HTMLInputElement;
    expect(checkOut.min).toBe('2026-09-01');
  });
});
