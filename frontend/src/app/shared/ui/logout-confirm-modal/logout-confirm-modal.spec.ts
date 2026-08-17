import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import type { LogoutGuardResponse } from '../../services/logout-guard.service';
import { LogoutConfirmModalComponent } from './logout-confirm-modal';

const GUARD: LogoutGuardResponse = {
  has_open_shifts: true,
  open_cash_shifts: [
    {
      id: 'shift-1',
      prop_id: 1,
      hotel_label: 'Hotel Lima Centro',
      shift_number: 1,
      shift_type: 'morning',
      shift_label: 'Matutino (08:00-16:00)',
      employee: 'Recep. Prueba',
      opened_by: 'recep.prueba',
      start_time: '2026-08-16T13:00:00+00:00',
    },
  ],
  open_attendance_shift: {
    id: 'att-1',
    employee_id: 'emp-1',
    employee_name: 'Recep. Prueba',
    date: '2026-08-16',
    scheduled_start: '08:00',
    scheduled_end: '16:00',
    area: 'Recepción',
    status: 'active',
  },
};

describe('LogoutConfirmModalComponent', () => {
  let fixture: ComponentFixture<LogoutConfirmModalComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LogoutConfirmModalComponent],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(LogoutConfirmModalComponent);
    fixture.componentRef.setInput('data', GUARD);
    fixture.detectChanges();
  });

  it('lists the open cash shift with its deep link', () => {
    const text = fixture.nativeElement.textContent ?? '';
    expect(text).toContain('Turno de caja abierto');
    expect(text).toContain('Hotel Lima Centro');
    expect(text).toContain('Matutino (08:00-16:00)');

    const links = fixture.nativeElement.querySelectorAll('a.lg-link');
    expect(links.length).toBe(2);
    expect(links[0].getAttribute('href')).toContain('/management/shifts/dashboard');
    expect(links[0].getAttribute('href')).toContain('prop_id=1');
  });

  it('lists the open attendance shift with the portal link', () => {
    const text = fixture.nativeElement.textContent ?? '';
    expect(text).toContain('Turno de asistencia activo');
    expect(text).toContain('08:00–16:00');

    const links = fixture.nativeElement.querySelectorAll('a.lg-link');
    expect(links[1].getAttribute('href')).toContain('/management/hr/portal/emp-1');
  });

  it('emits proceed when the user confirms logout anyway', () => {
    const spy = jest.fn();
    fixture.componentInstance.proceed.subscribe(spy);

    const buttons = [...fixture.nativeElement.querySelectorAll('button')] as HTMLElement[];
    const confirm = buttons.find((b) => b.textContent?.includes('de todos modos'));
    expect(confirm).toBeDefined();
    confirm!.click();

    expect(spy).toHaveBeenCalledTimes(1);
  });

  it('emits cancel on Escape', () => {
    const spy = jest.fn();
    fixture.componentInstance.cancel.subscribe(spy);

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));

    expect(spy).toHaveBeenCalledTimes(1);
  });

  it('emits cancel on overlay click', () => {
    const spy = jest.fn();
    fixture.componentInstance.cancel.subscribe(spy);

    const overlay = fixture.nativeElement.querySelector('.lg-modal-overlay') as HTMLElement;
    overlay.click();

    expect(spy).toHaveBeenCalledTimes(1);
  });
});
