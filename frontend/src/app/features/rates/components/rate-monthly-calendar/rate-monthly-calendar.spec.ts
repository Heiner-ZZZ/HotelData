import { TestBed } from '@angular/core/testing';

import { RateMonthlyCalendarComponent, type RoomTypeCalendarRow } from './rate-monthly-calendar';

describe('RateMonthlyCalendarComponent — marcador de entradas generadas (source=generated)', () => {
  function makeRow(source: string): RoomTypeCalendarRow[] {
    return [{
      roomTypeId: 'RT-1-STD',
      roomTypeName: 'Estándar',
      roomTypeNumber: 'STD',
      days: [{
        date: '2026-08-10',
        rateAmount: 120,
        ratePlanName: 'Flex',
        ratePlanId: 'RP-1',
        isClosed: false,
        minStay: 1,
        tier: 'medium',
        source,
      }],
    }];
  }

  function setup(row: RoomTypeCalendarRow[], displayMode: 'week' | 'month' = 'month') {
    TestBed.configureTestingModule({ imports: [RateMonthlyCalendarComponent] });
    const fixture = TestBed.createComponent(RateMonthlyCalendarComponent);
    const component = fixture.componentInstance;
    fixture.componentRef.setInput('rows', row);
    fixture.componentRef.setInput('month', 7);
    fixture.componentRef.setInput('year', 2026);
    fixture.componentRef.setInput('displayMode', displayMode);
    fixture.detectChanges();
    return { fixture, component };
  }

  it('marca la celda con el badge de generado cuando source=generated (vista mes)', () => {
    const { fixture } = setup(makeRow('generated'));
    const cell = (fixture.nativeElement as HTMLElement).querySelector('.cal-cell.has-rate') as HTMLElement;
    expect(cell).not.toBeNull();
    expect(cell.querySelector('.gen-badge')).not.toBeNull();
  });

  it('no marca la celda cuando la tarifa fue editada a mano (source vacío)', () => {
    const { fixture } = setup(makeRow(''));
    const cell = (fixture.nativeElement as HTMLElement).querySelector('.cal-cell.has-rate') as HTMLElement;
    expect(cell).not.toBeNull();
    expect(cell.querySelector('.gen-badge')).toBeNull();
  });

  it('marca la celda con el badge también en la vista semana', () => {
    const { fixture } = setup(makeRow('generated'), 'week');
    const cell = (fixture.nativeElement as HTMLElement).querySelector('.week-cell.has-rate') as HTMLElement;
    expect(cell).not.toBeNull();
    expect(cell.querySelector('.gen-badge')).not.toBeNull();
  });

  it('muestra la entrada "Generado" en la leyenda', () => {
    const { fixture } = setup(makeRow(''));
    const legend = (fixture.nativeElement as HTMLElement).querySelector('.cal-legend') as HTMLElement;
    expect(legend.textContent).toContain('Generado');
  });
});
