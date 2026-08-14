import { fakeAsync, flushMicrotasks, TestBed, tick } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { DestinationAutocompleteComponent } from './destination-autocomplete';

describe('DestinationAutocompleteComponent', () => {
  function setup() {
    TestBed.configureTestingModule({
      imports: [DestinationAutocompleteComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const fixture = TestBed.createComponent(DestinationAutocompleteComponent);
    const comp = fixture.componentInstance;
    fixture.detectChanges();
    return { fixture, comp, http: TestBed.inject(HttpTestingController) };
  }

  it('starts with no suggestions and closed dropdown', () => {
    const { comp } = setup();
    expect(comp.suggestions()).toEqual([]);
    expect(comp.dropdownOpen()).toBe(false);
  });

  it('filters suggestions as the user types (per-character)', fakeAsync(() => {
    const { fixture, comp, http } = setup();
    const input = fixture.nativeElement.querySelector('input') as HTMLInputElement;

    // El usuario enfoca el input y escribe "Ma" → debounce 250ms → petición q=Ma
    input.dispatchEvent(new Event('focus'));
    input.value = 'Ma';
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    tick(300);
    fixture.detectChanges();
    flushMicrotasks();

    const req = http.expectOne((r) => r.url.includes('/destinations/suggest') && r.url.includes('q=Ma'));
    req.flush({
      items: [
        { id: 1, name: 'Madrid' },
        { id: 2, name: 'Madrid Barajas' },
      ],
    });
    flushMicrotasks();
    fixture.detectChanges();
    expect(comp.suggestions().map((s) => s.name)).toEqual(['Madrid', 'Madrid Barajas']);
    expect(comp.dropdownOpen()).toBe(true);
  }));

  it('NO abre el dropdown cuando el valor llega precargado desde fuera (prefill sin interacción)', fakeAsync(() => {
    const { fixture, comp, http } = setup();
    fixture.componentRef.setInput('value', 'Hotel Lima Centro');
    fixture.detectChanges();
    tick(300);
    fixture.detectChanges();
    flushMicrotasks();

    const req = http.expectOne((r) => r.url.includes('/destinations/suggest'));
    req.flush({ items: [{ id: 7, name: 'Hotel Lima Centro', type: 'hotel' }] });
    flushMicrotasks();
    fixture.detectChanges();

    expect(comp.suggestions().length).toBe(1);
    expect(comp.dropdownOpen()).toBe(false);
  }));

  it('abre el dropdown al enfocar el input precargado (sugerencias ya cargadas)', fakeAsync(() => {
    const { fixture, comp, http } = setup();
    fixture.componentRef.setInput('value', 'Hotel Lima Centro');
    fixture.detectChanges();
    tick(300);
    fixture.detectChanges();
    flushMicrotasks();
    http.expectOne((r) => r.url.includes('/destinations/suggest')).flush({
      items: [{ id: 7, name: 'Hotel Lima Centro', type: 'hotel' }],
    });
    flushMicrotasks();
    fixture.detectChanges();

    expect(comp.dropdownOpen()).toBe(false);
    const input = fixture.nativeElement.querySelector('input') as HTMLInputElement;
    input.dispatchEvent(new Event('focus'));
    fixture.detectChanges();
    expect(comp.dropdownOpen()).toBe(true);
  }));

  it('selects a suggestion, fills the input and closes', () => {
    const { fixture, comp } = setup();
    const input = fixture.nativeElement.querySelector('input') as HTMLInputElement;
    let selected = '';
    comp.select.subscribe((name) => (selected = name));

    comp.suggestions.set([{ id: 1, name: 'Quito' }]);
    comp.dropdownOpen.set(true);
    fixture.detectChanges();

    const option = fixture.nativeElement.querySelectorAll('.da-option')[0] as HTMLElement;
    option.click();
    fixture.detectChanges();

    expect(selected).toBe('Quito');
    expect(input.value).toBe('Quito');
    expect(comp.dropdownOpen()).toBe(false);
  });

  it('emits valueChange as the user edits without selecting', () => {
    const { fixture, comp } = setup();
    const input = fixture.nativeElement.querySelector('input') as HTMLInputElement;
    let last = '';
    comp.valueChange.subscribe((v) => (last = v));

    input.value = 'Bar';
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    expect(last).toBe('Bar');
  });

  it('da al input un id/name propio (default destination-input) para el label del padre', () => {
    const { fixture } = setup();
    const input = fixture.nativeElement.querySelector('input.da-input') as HTMLInputElement;
    expect(input.id).toBe('destination-input');
    expect(input.name).toBe('destination-input');
  });

  it('respeta un inputId custom (p.ej. booking-bar-dest del booking-bar)', () => {
    const { fixture } = setup();
    fixture.componentRef.setInput('inputId', 'booking-bar-dest');
    fixture.detectChanges();
    const input = fixture.nativeElement.querySelector('input.da-input') as HTMLInputElement;
    expect(input.id).toBe('booking-bar-dest');
    expect(input.name).toBe('booking-bar-dest');
  });

  it('keeps the dropdown closed when suggestions are empty', () => {
    const { fixture, comp } = setup();
    const input = fixture.nativeElement.querySelector('input') as HTMLInputElement;
    input.value = 'zzz';
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    expect(comp.suggestions()).toEqual([]);
    expect(comp.dropdownOpen()).toBe(false);
  });

  it('renders a type chip and icon per suggestion (País/Hotel/Ciudad)', () => {
    const { fixture, comp } = setup();
    comp.suggestions.set([
      { id: 1, name: 'Madrid', type: 'city' },
      { id: 'XX-1', name: 'Hotel Lima', type: 'hotel' },
      { id: 42, name: 'Testlandia', type: 'country' },
    ]);
    comp.dropdownOpen.set(true);
    fixture.detectChanges();

    const options = fixture.nativeElement.querySelectorAll('.da-option');
    expect(options.length).toBe(3);
    const types = [...options].map((o) => (o as HTMLElement).querySelector('.da-option-type')?.textContent?.trim());
    expect(types).toEqual(['Ciudad', 'Hotel', 'País']);
    const icons = [...options].map((o) => (o as HTMLElement).querySelector('.da-option-icon')?.textContent?.trim());
    expect(icons).toEqual(['location_city', 'hotel', 'public']);
    expect(comp.typeLabel('hotel')).toBe('Hotel');
    expect(comp.typeLabel('country')).toBe('País');
    expect(comp.typeLabel('city')).toBe('Ciudad');
  });

  it('parses suggestions with an explicit type from the wire', fakeAsync(() => {
    const { fixture, comp, http } = setup();
    const input = fixture.nativeElement.querySelector('input') as HTMLInputElement;
    input.value = 'Lima';
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    tick(300);
    fixture.detectChanges();
    flushMicrotasks();
    const req = http.expectOne((r) => r.url.includes('/destinations/suggest') && r.url.includes('q=Lima'));
    req.flush({
      items: [
        { id: 7, name: 'Hotel Lima Centro', type: 'hotel' },
        { id: 169, name: 'Perú', type: 'country' },
      ],
    });
    flushMicrotasks();
    fixture.detectChanges();
    expect(comp.suggestions()[0].type).toBe('hotel');
    expect(comp.suggestions()[1].type).toBe('country');
  }));
});
