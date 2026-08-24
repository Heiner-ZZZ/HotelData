import { TestBed } from '@angular/core/testing';

import { buildCalendarMonth } from '../../availability.helpers';
import type { AvailabilityInventoryItem, AvailabilityRoomType } from '../../models/availability.model';
import { AvailabilityCalendarComponent } from './availability-calendar';

function inv(overrides: Partial<AvailabilityInventoryItem>): AvailabilityInventoryItem {
  return {
    date: '2026-09-01',
    roomTypeId: 'RT-STD',
    roomTypeName: 'Habitación Standard',
    totalRooms: 10,
    availableRooms: 5,
    blockedRooms: 0,
    occupancyLabel: '5/10 disponibles',
    occupancyPct: 50,
    hasRate: true,
    ...overrides,
  };
}

const ROOM_TYPES: AvailabilityRoomType[] = [
  { id: 'RT-STD', name: 'Habitación Standard', capacityLabel: '2 base · 2 adultos · 1 niños', isActive: true },
];

describe('AvailabilityCalendarComponent — marcador disponible sin tarifa', () => {
  function setup(items: AvailabilityInventoryItem[]) {
    TestBed.configureTestingModule({ imports: [AvailabilityCalendarComponent] });
    const fixture = TestBed.createComponent(AvailabilityCalendarComponent);
    fixture.componentRef.setInput('calendar', buildCalendarMonth(2026, 8, items));
    fixture.componentRef.setInput('roomTypes', ROOM_TYPES);
    fixture.componentRef.setInput('viewMode', 'month');
    fixture.componentRef.setInput('layoutMode', 'scroll');
    fixture.detectChanges();
    return fixture;
  }

  it('marca con cell-no-rate la celda con disponibilidad pero sin tarifa', () => {
    const fixture = setup([
      inv({ date: '2026-09-01', hasRate: true }),
      inv({ date: '2026-09-02', hasRate: false }),
    ]);
    const cells = fixture.nativeElement.querySelectorAll('td.cal-td-cell');
    const withRate = [...cells].find((c) => (c as HTMLElement).getAttribute('title')?.startsWith('2026-09-01'));
    const noRate = [...cells].find((c) => (c as HTMLElement).getAttribute('title')?.startsWith('2026-09-02'));
    expect(withRate?.classList.contains('cell-no-rate')).toBe(false);
    expect(noRate?.classList.contains('cell-no-rate')).toBe(true);
    // El marcador visual (punto ámbar) solo está en la celda sin tarifa.
    expect(noRate?.querySelector('.cell-no-rate-dot')).toBeTruthy();
    expect(withRate?.querySelector('.cell-no-rate-dot')).toBeFalsy();
  });

  it('NO marca una celda ocupada (disponible 0) aunque no tenga tarifa', () => {
    const fixture = setup([inv({ date: '2026-09-02', availableRooms: 0, hasRate: false })]);
    const cells = fixture.nativeElement.querySelectorAll('td.cal-td-cell');
    const cell = [...cells].find((c) => (c as HTMLElement).getAttribute('title')?.startsWith('2026-09-02'));
    expect(cell?.classList.contains('cell-no-rate')).toBe(false);
  });

  it('muestra la leyenda "Disponible sin tarifa"', () => {
    const fixture = setup([inv({ date: '2026-09-01', hasRate: false })]);
    const legend = fixture.nativeElement.querySelector('.cal-legend') as HTMLElement;
    expect(legend.textContent).toContain('Disponible sin tarifa');
  });
});

describe('AvailabilityCalendarComponent — contador de noches sin tarifa', () => {
  function setup(items: AvailabilityInventoryItem[]) {
    TestBed.configureTestingModule({ imports: [AvailabilityCalendarComponent] });
    const fixture = TestBed.createComponent(AvailabilityCalendarComponent);
    fixture.componentRef.setInput('calendar', buildCalendarMonth(2026, 8, items));
    fixture.componentRef.setInput('roomTypes', ROOM_TYPES);
    fixture.componentRef.setInput('viewMode', 'month');
    fixture.componentRef.setInput('layoutMode', 'scroll');
    fixture.detectChanges();
    return fixture;
  }

  function summary(fixture: ReturnType<typeof setup>) {
    return (fixture.nativeElement as HTMLElement).querySelector('.cal-summary') as HTMLElement;
  }

  it('cuenta noches ÚNICAS con disponibilidad sin tarifa en el rango (no celdas)', () => {
    // 09-02 y 09-03 sin tarifa (2 noches); la 09-02 además con 2 room types.
    const fixture = setup([
      inv({ date: '2026-09-01', hasRate: true }),
      inv({ date: '2026-09-02', hasRate: false }),
      inv({ date: '2026-09-02', roomTypeName: 'Habitación Deluxe', hasRate: false }),
      inv({ date: '2026-09-03', hasRate: false }),
    ]);
    expect(summary(fixture)!.textContent).toContain('2 noches disponibles sin tarifa');
  });

  it('no muestra el contador cuando todas las noches del rango tienen tarifa', () => {
    const fixture = setup([
      inv({ date: '2026-09-01', hasRate: true }),
      inv({ date: '2026-09-02', hasRate: true }),
    ]);
    expect(summary(fixture)!.textContent).not.toContain('sin tarifa');
  });

  it('no cuenta noches ocupadas aunque no tengan tarifa', () => {
    const fixture = setup([
      inv({ date: '2026-09-02', availableRooms: 0, hasRate: false }),
      inv({ date: '2026-09-03', availableRooms: 2, hasRate: false }),
    ]);
    expect(summary(fixture)!.textContent).toContain('1 noche disponible sin tarifa');
  });

  it('no cuenta noches pasadas sin tarifa — solo actuales y futuras (TDD)', () => {
    // Hoy es 2026-08-23. Usamos agosto 2026 para tener pasado (20) y futuro (25).
    // Este test necesita un calendario de agosto, no septiembre.
    TestBed.configureTestingModule({ imports: [AvailabilityCalendarComponent] });
    const fixture = TestBed.createComponent(AvailabilityCalendarComponent);
    fixture.componentRef.setInput('calendar', buildCalendarMonth(2026, 7, [
      inv({ date: '2026-08-20', hasRate: false }),
      inv({ date: '2026-08-25', hasRate: false }),
    ]));
    fixture.componentRef.setInput('roomTypes', ROOM_TYPES);
    fixture.componentRef.setInput('viewMode', 'month');
    fixture.componentRef.setInput('layoutMode', 'scroll');
    fixture.detectChanges();
    const summ = (fixture.nativeElement as HTMLElement).querySelector('.cal-summary') as HTMLElement;
    // Con el bug actual cuenta 2 (incluye pasado); debe ser 1
    expect(summ.textContent).toContain('1 noche disponible sin tarifa');
    expect(summ.textContent).not.toContain('2 noches');
  });
});

describe('AvailabilityCalendarComponent — noches sin tarifa excluyen pasado (TDD visual)', () => {
  function setup(items: AvailabilityInventoryItem[]) {
    TestBed.configureTestingModule({ imports: [AvailabilityCalendarComponent] });
    const fixture = TestBed.createComponent(AvailabilityCalendarComponent);
    // Usamos agosto 2026 para tener días pasados (20) y futuros (25) respecto a hoy 2026-08-23
    fixture.componentRef.setInput('calendar', buildCalendarMonth(2026, 7, items));
    fixture.componentRef.setInput('roomTypes', ROOM_TYPES);
    fixture.componentRef.setInput('viewMode', 'month');
    fixture.componentRef.setInput('layoutMode', 'scroll');
    fixture.detectChanges();
    return fixture;
  }

  it('no marca con cell-no-rate una noche pasada aunque tenga disponibilidad sin tarifa', () => {
    const fixture = setup([
      inv({ date: '2026-08-20', hasRate: false }),
      inv({ date: '2026-08-25', hasRate: false }),
    ]);
    const cells = fixture.nativeElement.querySelectorAll('td.cal-td-cell');
    const pastCell = [...cells].find((c) => (c as HTMLElement).getAttribute('title')?.startsWith('2026-08-20'));
    const futureCell = [...cells].find((c) => (c as HTMLElement).getAttribute('title')?.startsWith('2026-08-25'));
    expect(pastCell?.classList.contains('cell-no-rate')).toBe(false);
    expect(pastCell?.querySelector('.cell-no-rate-dot')).toBeFalsy();
    expect(futureCell?.classList.contains('cell-no-rate')).toBe(true);
    expect(futureCell?.querySelector('.cell-no-rate-dot')).toBeTruthy();
  });
});
