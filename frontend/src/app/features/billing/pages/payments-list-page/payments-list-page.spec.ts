import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of, Subject } from 'rxjs';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { AuthService } from '../../../../core/auth/auth.service';
import { BillingApiService } from '../../services/billing-api.service';
import type { PaymentListItem } from '../../models/billing.model';
import { PaymentsListPageComponent } from './payments-list-page';

describe('PaymentsListPageComponent', () => {
  /** confirmResult: null = cancela; string = motivo que confirma el reembolso. */
  function setup(confirmResult: string | null = 'Motivo de prueba') {
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const propertyContext = {
      ready: signal(false),
      singleHotelMode: signal(false),
      currentPropId: signal(1),
      currentCurrency: signal('USD'),
      setProperty: jest.fn(),
      clear: jest.fn(),
    } as unknown as PropertyContextService;
    const api = {
      getPayments: jest.fn(() => of({
        items: [], page: 1, pageSize: 10, total: 0, totalPages: 0, hasPrev: false, hasNext: false,
      })),
      refundPayment: jest.fn(() => of({})),
      createPayment: jest.fn(() => of({})),
      getShiftOptions: jest.fn(() => of([{ id: 'shift-1', label: 'morning · Carlos · 09/08 06:00' }])),
    } as unknown as BillingApiService;
    const auth = { hasPermission: jest.fn(() => true) } as unknown as AuthService;
    const confirmDialog = {
      open: jest.fn(() => Promise.resolve(true)),
      openPrompt: jest.fn(() => Promise.resolve(confirmResult)),
    } as unknown as ConfirmDialogService;

    TestBed.configureTestingModule({
      imports: [PaymentsListPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParamMap: convertToParamMap({ prop_id: '1', prop_label: 'Hotel Test' }) },
            queryParamMap: of(convertToParamMap({ prop_id: '1' })),
          },
        },
        { provide: PropertyContextService, useValue: propertyContext },
        { provide: BillingApiService, useValue: api },
        { provide: AuthService, useValue: auth },
        { provide: ConfirmDialogService, useValue: confirmDialog },
      ],
    });

    const fixture = TestBed.createComponent(PaymentsListPageComponent);
    fixture.detectChanges();
    return {
      fixture,
      component: fixture.componentInstance,
      toast: TestBed.inject(ToastService),
      api,
      confirmDialog,
      router,
    };
  }

  const payment = {
    id: 'P-1',
    bookingId: 'BK-1',
    invoiceId: 'INV-1',
    refundId: null,
    refundDocumentId: null,
    refundDocumentNumber: null,
    reconciliationStatus: null,
    reconciliationReason: null,
    amount: 109,
    method: 'card',
    status: 'confirmed',
    reference: 'REF-123',
    paidAt: '2026-08-09 10:00',
  } as PaymentListItem;

  it('no llama al API de reembolso si el usuario cancela la confirmación', async () => {
    const ctx = setup(null);

    await ctx.component.refund(payment);

    expect(ctx.api.refundPayment).not.toHaveBeenCalled();
    expect(ctx.component.refundingId()).toBeNull();
  });

  it('abre el modal de confirmación global en modo delete con el detalle del pago y un campo de motivo', async () => {
    const ctx = setup();

    await ctx.component.refund(payment);

    expect(ctx.confirmDialog.openPrompt).toHaveBeenCalledWith(expect.objectContaining({
      title: 'Reembolsar pago',
      message: '¿Reembolsar este pago? El cobro se revierte y no se puede deshacer.',
      confirmLabel: 'Reembolsar',
      variant: 'danger',
      mode: 'delete',
      modeDetail: 'REF-123',
      input: expect.objectContaining({ label: 'Motivo del reembolso (opcional)' }),
    }));
  });

  it('llama al API con el id del pago, el hotel y el motivo cuando se confirma, y muestra el toast', async () => {
    const ctx = setup('Cobro duplicado');

    await ctx.component.refund(payment);

    expect(ctx.api.refundPayment).toHaveBeenCalledWith('P-1', 1, undefined, 'Cobro duplicado');
    expect(ctx.toast.toasts().some((t) => t.message === 'Pago reembolsado correctamente.' && t.type === 'info')).toBe(true);
  });

  it('permite confirmar sin motivo (envía string vacío)', async () => {
    const ctx = setup('');

    await ctx.component.refund(payment);

    expect(ctx.api.refundPayment).toHaveBeenCalledWith('P-1', 1, undefined, '');
  });

  it('muestra el empleado del turno responsable del pago en la columna de atribución', () => {
    const ctx = setup();
    const withShift = {
      ...payment,
      shiftId: 'shift-1',
      shiftEmployee: 'Carlos Pérez',
      shiftOpenedBy: 'superadmin',
      shiftType: 'morning',
    } as PaymentListItem;

    expect(ctx.component.shiftLabel(withShift)).toBe('Carlos Pérez');
    expect(ctx.component.shiftTitle(withShift)).toContain('shift-1');
    expect(ctx.component.shiftTitle(withShift)).toContain('morning');
  });

  it('prioriza el turno del reembolso cuando el pago fue reembolsado', () => {
    const ctx = setup();
    const refunded = {
      ...payment,
      status: 'refunded',
      shiftId: 'shift-1',
      shiftEmployee: 'Carlos Pérez',
      refundShiftId: 'shift-9',
      refundShiftEmployee: 'María Gómez',
    } as PaymentListItem;

    expect(ctx.component.shiftLabel(refunded)).toBe('María Gómez');
    expect(ctx.component.shiftTitle(refunded)).toContain('shift-9');
  });

  it('cae a opened_by cuando no hay employee y muestra guion sin turno', () => {
    const ctx = setup();
    const noEmployee = {
      ...payment,
      shiftId: 'shift-2',
      shiftEmployee: null,
      shiftOpenedBy: 'gerente1',
    } as PaymentListItem;

    expect(ctx.component.shiftLabel(noEmployee)).toBe('gerente1');
    expect(ctx.component.shiftLabel(payment)).toBeNull();
  });

  it('envía sin_turno=true al API al activar el filtro Sin turno', () => {
    const ctx = setup();
    ctx.api.getPayments = jest.fn(() => of({
      items: [], page: 1, pageSize: 10, total: 0, totalPages: 0, hasPrev: false, hasNext: false,
    }));

    ctx.component.toggleSinTurno();
    ctx.fixture.detectChanges();

    expect(ctx.component.sinTurno()).toBe(true);
    expect(ctx.api.getPayments).toHaveBeenCalledWith(
      1,
      expect.objectContaining({ prop_id: 1, sin_turno: true }),
    );
  });

  it('carga las opciones de turno del hotel al inicializar y las muestra en el select de auditoría', () => {
    const ctx = setup();

    expect(ctx.api.getShiftOptions).toHaveBeenCalledWith(1);
    expect(ctx.component.shiftOptions()).toEqual([{ id: 'shift-1', label: 'morning · Carlos · 09/08 06:00' }]);

    const el = ctx.fixture.nativeElement as HTMLElement;
    const select = el.querySelector('.pay-audit-select') as HTMLSelectElement;
    expect(select).toBeTruthy();
    expect(select.querySelectorAll('option').length).toBe(2); // 'Todos los turnos' + shift-1
  });

  it('filtra por turno: navega con el query param turno', () => {
    const ctx = setup();

    ctx.component.setTurnoFilter('shift-1');
    ctx.fixture.detectChanges();

    expect(ctx.router.navigate).toHaveBeenCalledWith([], expect.objectContaining({
      queryParams: expect.objectContaining({ turno: 'shift-1' }),
    }));
  });

  it('filtra por cajero: navega con el query param cajero', () => {
    const ctx = setup();

    ctx.component.setCajeroFilter('Carlos');
    ctx.fixture.detectChanges();

    expect(ctx.router.navigate).toHaveBeenCalledWith([], expect.objectContaining({
      queryParams: expect.objectContaining({ cajero: 'Carlos' }),
    }));
  });

  it('limpiar filtros de auditoría remueve turno y cajero de la URL y apaga el chip Sin turno', () => {
    const ctx = setup();

    ctx.component.toggleSinTurno();
    ctx.component.clearAllFilters();
    ctx.fixture.detectChanges();

    expect(ctx.component.sinTurno()).toBe(false);
    expect(ctx.router.navigate).toHaveBeenCalledWith([], expect.objectContaining({
      queryParams: expect.objectContaining({ turno: null, cajero: null }),
    }));
  });

  it('permite vincular solo pagos sin turno con permiso de gestión', () => {
    const ctx = setup();
    const withShift = { ...payment, shiftId: 'shift-1', shiftEmployee: 'Carlos' } as PaymentListItem;

    expect(ctx.component.canLink(payment)).toBe(true);
    expect(ctx.component.canLink(withShift)).toBe(false);
  });

  it('muestra un badge contador en el chip Sin turno con los pagos legacy pendientes del hotel', () => {
    const ctx = setup();
    ctx.api.getPayments = jest.fn(() => of({
      items: [payment], page: 1, pageSize: 10, total: 1, totalPages: 1,
      hasPrev: false, hasNext: false, legacyPendingCount: 4,
    }));
    ctx.component.paymentsResource.reload();
    ctx.fixture.detectChanges();

    const el = ctx.fixture.nativeElement as HTMLElement;
    const chip = [...el.querySelectorAll('button')].find(b => b.textContent?.includes('Sin turno'));
    expect(chip).toBeTruthy();
    const badge = chip!.querySelector('.sin-turno-badge');
    expect(badge?.textContent?.trim()).toBe('4');
  });

  it('oculta el badge cuando el hotel no tiene pagos legacy pendientes', () => {
    const ctx = setup();
    ctx.api.getPayments = jest.fn(() => of({
      items: [payment], page: 1, pageSize: 10, total: 1, totalPages: 1,
      hasPrev: false, hasNext: false, legacy_pending_count: 0,
    }));
    ctx.component.paymentsResource.reload();
    ctx.fixture.detectChanges();

    const el = ctx.fixture.nativeElement as HTMLElement;
    const chip = [...el.querySelectorAll('button')].find(b => b.textContent?.includes('Sin turno'));
    expect(chip).toBeTruthy();
    expect(chip!.querySelector('.sin-turno-badge')).toBeFalsy();
  });

  it('abre el modal de vínculo con el pago seleccionado y recarga al vincularse', async () => {
    const ctx = setup();
    ctx.api.getPayments = jest.fn(() => of({
      items: [], page: 1, pageSize: 10, total: 0, totalPages: 0, hasPrev: false, hasNext: false,
    }));

    ctx.component.openLinkShift(payment);
    expect(ctx.component.linkingPayment()).toEqual(payment);

    ctx.component.onPaymentLinked();
    ctx.fixture.detectChanges();
    expect(ctx.component.linkingPayment()).toBeNull();
    expect(ctx.toast.toasts().some((t) => t.message === 'Pago vinculado al turno correctamente.' && t.type === 'info')).toBe(true);
    expect(ctx.api.getPayments).toHaveBeenCalled();
  });
});
