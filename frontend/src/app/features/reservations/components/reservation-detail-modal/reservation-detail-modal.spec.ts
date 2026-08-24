import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { CheckInsApiService } from '../../../check-ins/services/check-ins-api.service';
import { InStayApiService } from '../../../in-stay/services/in-stay-api.service';
import { ToastService } from '../../../../shared/services/toast.service';
import type { ReceptionCalendarReservation } from '../../models/reception-calendar.model';
import { ReservationDetailModalComponent } from './reservation-detail-modal';

function reservation(overrides: Partial<ReceptionCalendarReservation> = {}): ReceptionCalendarReservation {
  return {
    bookingId: 'BK-CAL-1',
    guestName: 'Cliente Demo',
    adults: 1,
    children: 0,
    checkInDate: '2026-08-14',
    checkInTime: '15:00',
    estimatedArrivalTime: '',
    lateCheckin: false,
    checkOutDate: '2026-08-16',
    checkOutTime: '12:00',
    totalNights: 2,
    status: 'confirmed',
    stayStatus: 'no_show',
    visualStatus: 'active',
    reopenWindow: 'open',
    assignedRooms: ['HR-1'],
    hotelRoomId: 'HR-1',
    roomNumber: '101',
    totalPrice: 100,
    currency: 'USD',
    ...overrides,
  };
}

async function render(opts: {
  reservationOverrides?: Partial<ReceptionCalendarReservation>;
  hasPermission?: boolean;
  reopenNoShow?: jest.Mock;
}) {
  const reopenNoShow = opts.reopenNoShow ?? jest.fn(() => of({ ok: true }));
  const hasPermission = jest.fn(() => opts.hasPermission ?? true);
  const toast = { error: jest.fn(), success: jest.fn() };
  await TestBed.configureTestingModule({
    imports: [ReservationDetailModalComponent],
    providers: [
      provideHttpClient(),
      provideHttpClientTesting(),
      { provide: Router, useValue: { events: of(), navigate: jest.fn() } },
      {
        provide: ActivatedRoute,
        useValue: {
          snapshot: { data: {} },
          url: of([]),
          params: of({}),
          queryParams: of({}),
          fragment: of(null),
        },
      },
      { provide: ToastService, useValue: toast },
      { provide: AuthService, useValue: { hasPermission } },
      { provide: InStayApiService, useValue: { getMyStaySession: jest.fn(() => of({ token: 'x' })) } },
      { provide: CheckInsApiService, useValue: { reopenNoShow } },
    ],
  }).compileComponents();

  const fixture = TestBed.createComponent(ReservationDetailModalComponent);
  fixture.componentRef.setInput('reservation', reservation(opts.reservationOverrides ?? {}));
  fixture.detectChanges();
  TestBed.inject(HttpTestingController)
    .expectOne((r) => r.url.includes('/reservations/BK-CAL-1'))
    .flush({ booking: { booking_id: 'BK-CAL-1', stay_status: 'no_show' } });
  // El valor del httpResource aterriza en microtasks internas; esperar a que
  // el estado 'value' se asiente antes de leer el template (mismo patrón que
  // el spec del check-in detail).
  await Promise.resolve();
  await Promise.resolve();
  fixture.detectChanges();
  return { fixture, hasPermission, reopenNoShow, toast };
}

function text(fixture: ComponentFixture<ReservationDetailModalComponent>): string {
  return (fixture.nativeElement as HTMLElement).textContent ?? '';
}

function findButton(fixture: ComponentFixture<ReservationDetailModalComponent>, label: string): HTMLButtonElement | null {
  return Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button')).find(
    (b) => (b.textContent ?? '').includes(label),
  ) ?? null;
}

describe('ReservationDetailModalComponent — ventana de reapertura de no-show', () => {
  it('muestra la acción Reabrir no-show solo dentro de la ventana y con permiso gerencial', async () => {
    const { fixture, hasPermission } = await render({
      reservationOverrides: { stayStatus: 'no_show', reopenWindow: 'open' },
      hasPermission: true,
    });

    expect(findButton(fixture, 'Reabrir no-show')).not.toBeNull();
    expect(text(fixture)).toContain('reapertura abierta');
    expect(hasPermission).toHaveBeenCalledWith('check-ins.no_show_reopen');
  });

  it('oculta la acción en no-shows antiguos (ventana cerrada por retraso) y orienta a nueva reserva', async () => {
    const { fixture } = await render({
      reservationOverrides: { stayStatus: 'no_show', reopenWindow: 'too_late' },
      hasPermission: true,
    });

    expect(findButton(fixture, 'Reabrir no-show')).toBeNull();
    const t = text(fixture).toLowerCase();
    expect(t).toContain('ventana de reapertura cerrada');
    expect(t).toContain('ajustá las fechas');
  });

  it('oculta la acción cuando la estadía terminó', async () => {
    const { fixture } = await render({
      reservationOverrides: { stayStatus: 'no_show', reopenWindow: 'stay_ended', visualStatus: 'past' },
      hasPermission: true,
    });

    expect(findButton(fixture, 'Reabrir no-show')).toBeNull();
    expect(text(fixture)).toContain('estadía ya terminó');
  });

  it('oculta la acción aunque la ventana esté abierta si falta el permiso gerencial', async () => {
    const { fixture } = await render({
      reservationOverrides: { stayStatus: 'no_show', reopenWindow: 'open' },
      hasPermission: false,
    });

    expect(findButton(fixture, 'Reabrir no-show')).toBeNull();
    expect(text(fixture)).not.toContain('Reabrir no-show');
  });

  it('reabre con motivo: llama a la API, emite reopened y muestra toast de éxito', async () => {
    const reopenNoShow = jest.fn(() => of({ ok: true }));
    const { fixture, reopenNoShow: api, toast } = await render({
      reservationOverrides: { stayStatus: 'no_show', reopenWindow: 'open' },
      hasPermission: true,
      reopenNoShow,
    });
    const reopened = jest.fn();
    fixture.componentInstance.reopened.subscribe(reopened);

    findButton(fixture, 'Reabrir no-show')!.click();
    fixture.detectChanges();
    const textarea = (fixture.nativeElement as HTMLElement).querySelector<HTMLTextAreaElement>('#rd-reopen-reason')!;
    textarea.value = 'El huésped llegó tras el cierre del no-show';
    textarea.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    findButton(fixture, 'Reabrir reserva')!.click();
    fixture.detectChanges();

    expect(api).toHaveBeenCalledWith('BK-CAL-1', 'El huésped llegó tras el cierre del no-show', undefined);
    expect(reopened).toHaveBeenCalledTimes(1);
    expect(toast.success).toHaveBeenCalledWith('Reserva reabierta — el huésped puede hacer check-in.');
  });

  it('exige motivo: no llama a la API sin texto en el motivo', async () => {
    const reopenNoShow = jest.fn(() => of({ ok: true }));
    const { fixture, reopenNoShow: api } = await render({
      reservationOverrides: { stayStatus: 'no_show', reopenWindow: 'open' },
      hasPermission: true,
      reopenNoShow,
    });

    findButton(fixture, 'Reabrir no-show')!.click();
    fixture.detectChanges();
    const confirm = findButton(fixture, 'Reabrir reserva')!;
    expect(confirm.disabled).toBe(true);
    expect(api).not.toHaveBeenCalled();
  });
});
