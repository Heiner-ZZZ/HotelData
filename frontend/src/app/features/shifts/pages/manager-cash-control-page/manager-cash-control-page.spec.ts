import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { Router } from '@angular/router';
import { ShiftsApiService, type ShiftInfo } from '../../services/shifts-api.service';
import { ManagerCashControlPageComponent } from './manager-cash-control-page';

function shiftFixture(overrides: Partial<ShiftInfo> = {}): ShiftInfo {
  return {
    id: 'shift-1',
    prop_id: 940,
    shift_type: 'morning',
    employee: 'Teller Demo',
    opened_by: 'gerente1',
    start_time: '2026-08-09T06:00:00',
    end_time: '2026-08-09T14:00:00',
    cash_initial: 100,
    cash_counted: 150,
    cash_final: 150,
    cash_left: 150,
    cash_over_short: 0,
    closing_notes: null,
    total_collected: 50,
    status: 'closed',
    closed_by: 'gerente1',
    closed_at: '2026-08-09T14:00:00',
    transactions: [],
    payment_ids: ['p-1', 'p-2'],
    employee_summary: [
      {
        employee: 'Carlos Pérez',
        count: 2,
        total: 80,
        cash: 50,
        card: 30,
        transfer: 0,
        other: 0,
      },
      {
        employee: 'María López',
        count: 1,
        total: 20,
        cash: 20,
        card: 0,
        transfer: 0,
        other: 0,
      },
    ],
    payments: [
      {
        payment_id: 'p-1',
        amount: 30,
        method: 'cash',
        reference: 'REF-1',
        paid_at: '2026-08-09T10:00:00',
        shift_employee: 'Carlos Pérez',
        shift_opened_by: 'gerente1',
        shift_type: 'morning',
      },
      {
        payment_id: 'p-2',
        amount: 20,
        method: 'card',
        reference: 'REF-2',
        paid_at: '2026-08-09T11:00:00',
        shift_employee: null,
        shift_opened_by: 'admin_test',
        shift_type: null,
      },
    ],
    ...overrides,
  };
}

function setup(shifts: ShiftInfo[]) {
  const api = {
    listShiftsForCashControl: jest.fn(() => of({ items: shifts, total: shifts.length })),
  } as unknown as ShiftsApiService;
  const propertyContext = {
    ready: signal(false),
    singleHotelMode: signal(false),
    currentPropId: signal(940),
    currentCurrency: signal('USD'),
    setProperty: jest.fn(),
    clear: jest.fn(),
  } as unknown as PropertyContextService;
  const toast = { error: jest.fn(), show: jest.fn() } as unknown as ToastService;
  const router = { navigate: jest.fn() } as unknown as Router;

  TestBed.configureTestingModule({
    imports: [ManagerCashControlPageComponent],
    providers: [
      { provide: ShiftsApiService, useValue: api },
      { provide: PropertyContextService, useValue: propertyContext },
      { provide: ToastService, useValue: toast },
      { provide: Router, useValue: router },
    ],
  });

  const fixture = TestBed.createComponent(ManagerCashControlPageComponent);
  fixture.detectChanges();
  return { fixture, component: fixture.componentInstance, api };
}

describe('ManagerCashControlPageComponent', () => {
  it('muestra la columna Responsable con el empleado estampado de cada pago', () => {
    const { fixture, component } = setup([shiftFixture()]);

    component.selectShift(component.shifts()[0]);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Responsable');
    expect(el.textContent).toContain('Carlos Pérez');
    expect(el.textContent).toContain('admin_test');
  });

  it('cae al opened_by cuando el pago no tiene shift_employee', () => {
    const { fixture, component } = setup([shiftFixture({
      payments: [{
        payment_id: 'p-2',
        amount: 20,
        method: 'card',
        reference: 'REF-2',
        paid_at: '2026-08-09T11:00:00',
        shift_employee: null,
        shift_opened_by: 'admin_test',
        shift_type: null,
      }],
    })]);

    component.selectShift(component.shifts()[0]);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('admin_test');
  });

  it('muestra guion cuando el pago no tiene atribución', () => {
    const { fixture, component } = setup([shiftFixture({
      payments: [{
        payment_id: 'p-3',
        amount: 20,
        method: 'card',
        reference: 'REF-3',
        paid_at: '2026-08-09T11:00:00',
        shift_employee: null,
        shift_opened_by: null,
        shift_type: null,
      }],
    })]);

    component.selectShift(component.shifts()[0]);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('REF-3');
    const row = [...el.querySelectorAll('tr')].find(r => r.textContent?.includes('REF-3'));
    expect(row?.textContent).toContain('—');
  });

  it('no muestra la sección de pagos cuando el turno no tiene pagos', () => {
    const { fixture, component } = setup([shiftFixture({ payment_ids: [], payments: [] })]);

    component.selectShift(component.shifts()[0]);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).not.toContain('Pagos del turno');
  });

  it('etiqueta cada transacción con su tipo (check-in / check-out / pago / cancelación)', () => {
    const { fixture, component } = setup([shiftFixture({
      transactions: [
        {
          transaction_id: 't-1',
          type: 'check_in',
          booking_id: 'BK-1',
          amount: 0,
          payment_method: '',
          timestamp: '2026-08-09T10:00:00',
          description: 'Check-in: Ana Pérez — Folio FL-1',
        },
        {
          transaction_id: 't-2',
          type: 'check_out',
          booking_id: 'BK-1',
          amount: 120,
          payment_method: 'cash',
          timestamp: '2026-08-09T11:00:00',
          description: 'Check-out: Ana Pérez — $120.00',
        },
        {
          transaction_id: 't-3',
          type: 'cancellation',
          booking_id: 'BK-2',
          amount: -20,
          payment_method: '',
          timestamp: '2026-08-09T12:00:00',
          description: 'Cancelación: Luis — razón: no show',
        },
      ],
    })]);

    component.selectShift(component.shifts()[0]);
    fixture.detectChanges();

    expect(component.transactionTypeLabel('check_in')).toBe('Check-in');
    expect(component.transactionTypeLabel('check_out')).toBe('Check-out');
    expect(component.transactionTypeLabel('payment')).toBe('Pago');
    expect(component.transactionTypeLabel('cancellation')).toBe('Cancelación');
    expect(component.transactionTypeLabel('otro')).toBe('otro');

    const el = fixture.nativeElement as HTMLElement;
    const rows = [...el.querySelectorAll('.mcc-txn-row')].map(r => r.textContent ?? '');
    expect(rows.length).toBe(3);
    expect(rows.some(r => r.includes('Check-in'))).toBe(true);
    expect(rows.some(r => r.includes('Check-out'))).toBe(true);
    expect(rows.some(r => r.includes('Cancelación'))).toBe(true);
    expect(rows.find(r => r.includes('Check-out'))).toContain('$120.00');
  });

  it('muestra líneas de firma manuscrita con Abierto por y Cerrado por en el arqueo', () => {
    const { fixture, component } = setup([shiftFixture()]);

    component.selectShift(component.shifts()[0]);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelectorAll('.mcc-signature-line').length).toBe(2);
    const text = el.textContent ?? '';
    expect(text).toContain('Abierto por');
    expect(text).toContain('gerente1');
    expect(text).toContain('Cerrado por');
    expect(text).toContain('Firma');
  });

  it('muestra el resumen por empleado con totales y desglose por método', () => {
    const { fixture, component } = setup([shiftFixture()]);

    component.selectShift(component.shifts()[0]);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Resumen por empleado');
    const rows = [...el.querySelectorAll('.mcc-emp-row')].map(r => r.textContent?.trim() ?? '');
    const carlos = rows.find(r => r.includes('Carlos Pérez'));
    expect(carlos).toBeTruthy();
    expect(carlos).toContain('2');
    expect(carlos).toContain('$80.00');
    expect(carlos).toContain('$50.00');
    expect(carlos).toContain('$30.00');
    expect(rows.find(r => r.includes('María López'))).toContain('$20.00');
  });

  it('agrupa bajo Sin atribución los pagos sin estampa en el resumen', () => {
    const { fixture, component } = setup([shiftFixture({
      employee_summary: [{
        employee: 'Sin atribución',
        count: 1,
        total: 10,
        cash: 10,
        card: 0,
        transfer: 0,
        other: 0,
      }],
    })]);

    component.selectShift(component.shifts()[0]);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    const rows = [...el.querySelectorAll('.mcc-emp-row')].map(r => r.textContent?.trim() ?? '');
    expect(rows.find(r => r.includes('Sin atribución'))).toContain('$10.00');
  });

  it('oculta el resumen por empleado cuando no hay pagos estampados', () => {
    const { fixture, component } = setup([shiftFixture({ employee_summary: [] })]);

    component.selectShift(component.shifts()[0]);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).not.toContain('Resumen por empleado');
  });

  it('el botón Imprimir del modal dispara window.print para exportar el arqueo a PDF', () => {
    const { fixture, component } = setup([shiftFixture()]);
    const printSpy = jest.spyOn(window, 'print').mockImplementation(() => {});

    component.selectShift(component.shifts()[0]);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    const btn = [...el.querySelectorAll('button')].find(b => b.textContent?.includes('Imprimir'));
    expect(btn).toBeTruthy();
    btn!.click();

    expect(printSpy).toHaveBeenCalled();
    printSpy.mockRestore();
  });

  it('el nombre sugerido del PDF del arqueo incluye hotel, turno y empleado', () => {
    const { fixture, component } = setup([shiftFixture()]);
    // El diálogo de guardado usa el título en el momento de imprimir; capturamos
    // el valor que el navegador vería dentro del print real antes del restore.
    let used = '';
    jest.spyOn(window, 'print').mockImplementation(() => { used = document.title; });
    component.onPropSelected({ propId: 940, label: 'Hotel Lima Centro' });

    component.selectShift(component.shifts()[0]);
    fixture.detectChanges();
    const btn = [...fixture.nativeElement.querySelectorAll('button')].find(b => b.textContent?.includes('Imprimir'));
    btn!.click();

    expect(used).toBe('Arqueo-Hotel-Lima-Centro-Matutino-Teller-Demo-2026-08-09');
  });

  it('restaura el título original del documento después de imprimir el arqueo', () => {
    const { fixture, component } = setup([shiftFixture()]);
    jest.spyOn(window, 'print').mockImplementation(() => {});
    document.title = 'HotelData — Título original';
    component.onPropSelected({ propId: 940, label: 'Hotel Lima Centro' });

    component.selectShift(component.shifts()[0]);
    fixture.detectChanges();
    const btn = [...fixture.nativeElement.querySelectorAll('button')].find(b => b.textContent?.includes('Imprimir'));
    btn!.click();

    expect(document.title).toBe('HotelData — Título original');
  });

  it('el encabezado de impresión del arqueo incluye el título, el hotel y el empleado', () => {
    const { fixture, component } = setup([shiftFixture()]);
    component.onPropSelected({ propId: 940, label: 'Hotel Lima Centro' });

    component.selectShift(component.shifts()[0]);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Arqueo de caja');
    expect(el.textContent).toContain('Hotel Lima Centro');
    expect(el.textContent).toContain('Teller Demo');
  });
});
