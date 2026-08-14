import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';

import { DateRangePickerComponent } from '../date-range-picker/date-range-picker';
import { DestinationAutocompleteComponent } from '../destination-autocomplete/destination-autocomplete';
import { GuestsPickerComponent } from '../guests-picker/guests-picker';
import { BookingSearchBarComponent, type BookingSearchValues } from './booking-search-bar';

describe('BookingSearchBarComponent — misma caja de búsqueda del welcome', () => {
  function setup(initial: Partial<BookingSearchValues> = {}) {
    TestBed.configureTestingModule({
      imports: [BookingSearchBarComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const fixture = TestBed.createComponent(BookingSearchBarComponent);
    const comp = fixture.componentInstance;
    fixture.componentRef.setInput('destination', initial.destination ?? '');
    fixture.componentRef.setInput('checkIn', initial.checkIn ?? '');
    fixture.componentRef.setInput('checkOut', initial.checkOut ?? '');
    fixture.componentRef.setInput('adults', initial.adults ?? 2);
    fixture.componentRef.setInput('children', initial.children ?? 0);
    fixture.componentRef.setInput('rooms', initial.rooms ?? 1);
    fixture.detectChanges();
    return { fixture, comp };
  }

  it('renderiza los tres campos (destino, fechas, huéspedes) y el CTA', () => {
    const { fixture } = setup();
    expect(fixture.debugElement.query(By.directive(DestinationAutocompleteComponent))).toBeTruthy();
    expect(fixture.debugElement.query(By.directive(DateRangePickerComponent))).toBeTruthy();
    expect(fixture.debugElement.query(By.directive(GuestsPickerComponent))).toBeTruthy();
    const cta = fixture.nativeElement.querySelector('.booking-bar__cta') as HTMLButtonElement;
    expect(cta).toBeTruthy();
    expect(cta.textContent).toContain('Buscar');
  });

  it('aplica los valores iniciales a los widgets', () => {
    const { fixture } = setup({ destination: 'Quito', checkIn: '2026-09-01', checkOut: '2026-09-03', adults: 3, children: 1, rooms: 2 });
    const daInput = fixture.nativeElement.querySelector('.da-input') as HTMLInputElement;
    expect(daInput.value).toBe('Quito');
    const drp = fixture.debugElement.query(By.directive(DateRangePickerComponent)).componentInstance as DateRangePickerComponent;
    expect(drp.startDate()).toBe('2026-09-01');
    expect(drp.endDate()).toBe('2026-09-03');
    const gp = fixture.debugElement.query(By.directive(GuestsPickerComponent)).componentInstance as GuestsPickerComponent;
    expect(gp.adults()).toBe(3);
    expect(gp.children()).toBe(1);
    expect(gp.rooms()).toBe(2);
  });

  it('emite search con destino, fechas y huéspedes al enviar', () => {
    const { fixture, comp } = setup();
    let emitted: BookingSearchValues | null = null;
    comp.search.subscribe((v) => (emitted = v));

    const daInput = fixture.nativeElement.querySelector('.da-input') as HTMLInputElement;
    daInput.value = 'Hotel Lima Centro';
    daInput.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const drp = fixture.debugElement.query(By.directive(DateRangePickerComponent)).componentInstance as DateRangePickerComponent;
    drp.startChange.emit('2026-09-01');
    drp.endChange.emit('2026-09-03');
    const gp = fixture.debugElement.query(By.directive(GuestsPickerComponent)).componentInstance as GuestsPickerComponent;
    gp.adultsChange.emit(2);
    gp.childrenChange.emit(1);
    gp.roomsChange.emit(1);
    fixture.detectChanges();

    comp.submit();
    expect(emitted).toEqual({
      destination: 'Hotel Lima Centro',
      checkIn: '2026-09-01',
      checkOut: '2026-09-03',
      adults: 2,
      children: 1,
      rooms: 1,
    });
  });

  it('emite valueChange al cambiar el destino (para persistencia en vivo)', () => {
    const { fixture, comp } = setup();
    let changed: BookingSearchValues | null = null;
    comp.valueChange.subscribe((v) => (changed = v));

    const daInput = fixture.nativeElement.querySelector('.da-input') as HTMLInputElement;
    daInput.value = 'Madrid';
    daInput.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    expect(changed?.destination).toBe('Madrid');
  });

  it('openDateRange abre el calendario del date-range-picker', () => {
    const { fixture, comp } = setup();
    const drp = fixture.debugElement.query(By.directive(DateRangePickerComponent)).componentInstance as DateRangePickerComponent;
    expect(drp.isOpen()).toBe(false);
    comp.openDateRange();
    fixture.detectChanges();
    expect(drp.isOpen()).toBe(true);
  });

  it('el botón limpiar está deshabilitado con los valores por defecto', () => {
    const { fixture } = setup();
    const btn = fixture.nativeElement.querySelector('.booking-bar__clear') as HTMLButtonElement;
    expect(btn).toBeTruthy();
    expect(btn.disabled).toBe(true);
  });

  it('el botón limpiar se habilita cuando hay contenido en algún filtro', () => {
    const { fixture } = setup({ destination: 'Quito' });
    const btn = fixture.nativeElement.querySelector('.booking-bar__clear') as HTMLButtonElement;
    expect(btn.disabled).toBe(false);
  });

  it('limpiar resetea los tres filtros (destino, fechas, huéspedes) y emite search', () => {
    const { fixture, comp } = setup({ destination: 'Quito', checkIn: '2026-09-01', checkOut: '2026-09-03', adults: 3, children: 1, rooms: 2 });
    let emitted: BookingSearchValues | null = null;
    comp.search.subscribe((v) => (emitted = v));

    comp.clearFilters();
    fixture.detectChanges();

    expect((fixture.nativeElement.querySelector('.da-input') as HTMLInputElement).value).toBe('');
    const drp = fixture.debugElement.query(By.directive(DateRangePickerComponent)).componentInstance as DateRangePickerComponent;
    expect(drp.startDate()).toBe('');
    expect(drp.endDate()).toBe('');
    expect(emitted).toEqual({ destination: '', checkIn: '', checkOut: '', adults: 2, children: 0, rooms: 1 });
    // tras limpiar, el botón vuelve a deshabilitarse
    expect((fixture.nativeElement.querySelector('.booking-bar__clear') as HTMLButtonElement).disabled).toBe(true);
  });

  it('el label "Destino" apunta al input del autocomplete (for == id), sin errores de Issues', () => {
    const { fixture } = setup();
    const label = fixture.nativeElement.querySelector('label[for]') as HTMLLabelElement;
    const input = fixture.nativeElement.querySelector('input.da-input') as HTMLInputElement;
    expect(label).toBeTruthy();
    expect(label.htmlFor).toBeTruthy();
    expect(label.htmlFor).toBe(input.id);
    expect(input.id).toBe('booking-bar-dest');
    expect(input.name).toBe('booking-bar-dest');
  });

  it('aplica la clase compact cuando compact=true', () => {
    const { fixture } = setup();
    fixture.componentRef.setInput('compact', true);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('form.booking-bar--compact')).toBeTruthy();
  });
});
