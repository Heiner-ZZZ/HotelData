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
import type { InvoiceListItem } from '../../models/billing.model';
import { InvoicesListPageComponent } from './invoices-list-page';

describe('InvoicesListPageComponent', () => {
  /** confirmResult: null = cancela; string = motivo que confirma la anulación. */
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
      getInvoices: jest.fn(() => of({
        items: [], page: 1, pageSize: 10, total: 0, totalPages: 0, hasPrev: false, hasNext: false,
      })),
      getInvoiceStats: jest.fn(() => of({
        issued: { count: 0, total: 0 }, paid: { count: 0, total: 0 },
        cancelled: { count: 0, total: 0 }, refunded: { count: 0, total: 0 },
      })),
      cancelInvoice: jest.fn(() => of({})),
      getShiftOptions: jest.fn(() => of([{ id: 'shift-1', label: 'morning · Carlos · 09/08 06:00' }])),
    } as unknown as BillingApiService;
    const auth = { hasPermission: jest.fn(() => true) } as unknown as AuthService;
    const confirmDialog = {
      open: jest.fn(() => Promise.resolve(true)),
      openPrompt: jest.fn(() => Promise.resolve(confirmResult)),
    } as unknown as ConfirmDialogService;

    TestBed.configureTestingModule({
      imports: [InvoicesListPageComponent],
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

    const fixture = TestBed.createComponent(InvoicesListPageComponent);
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

  const invoice = {
    id: 'INV-1',
    bookingId: 'BK-1',
    invoiceNumber: 'FAC-202608-0001',
    subtotal: 100,
    taxes: 16,
    total: 116,
    status: 'issued',
    issuedAt: '2026-08-09T10:00:00',
    paidAt: null,
  } as InvoiceListItem;

  it('no llama al API de anulación si el usuario cancela la confirmación', async () => {
    const ctx = setup(null);

    await ctx.component.cancelInvoice(invoice);

    expect(ctx.api.cancelInvoice).not.toHaveBeenCalled();
  });

  it('abre el modal de confirmación global en modo delete con el detalle de la factura y un campo de motivo', async () => {
    const ctx = setup();

    await ctx.component.cancelInvoice(invoice);

    expect(ctx.confirmDialog.openPrompt).toHaveBeenCalledWith(expect.objectContaining({
      title: 'Anular factura',
      message: '¿Anular esta factura? Esta acción no se puede deshacer.',
      confirmLabel: 'Anular factura',
      variant: 'danger',
      mode: 'delete',
      modeDetail: 'FAC-202608-0001',
      input: expect.objectContaining({ label: 'Motivo de la anulación (opcional)' }),
    }));
  });

  it('llama al API con el id de la factura, el hotel y el motivo cuando se confirma, y muestra el toast', async () => {
    const ctx = setup('Factura duplicada');

    await ctx.component.cancelInvoice(invoice);

    expect(ctx.api.cancelInvoice).toHaveBeenCalledWith('INV-1', 1, 'Factura duplicada');
    expect(ctx.toast.toasts().some((t) => t.message === 'Factura anulada correctamente.' && t.type === 'info')).toBe(true);
  });

  it('permite anular sin motivo (envía string vacío)', async () => {
    const ctx = setup('');

    await ctx.component.cancelInvoice(invoice);

    expect(ctx.api.cancelInvoice).toHaveBeenCalledWith('INV-1', 1, '');
  });

  it('solo permite anular facturas en estado emitida', () => {
    const ctx = setup();

    expect(ctx.component.canCancel({ ...invoice, status: 'issued' })).toBe(true);
    expect(ctx.component.canCancel({ ...invoice, status: 'paid' })).toBe(false);
    expect(ctx.component.canCancel({ ...invoice, status: 'cancelled' })).toBe(false);
    expect(ctx.component.canCancel({ ...invoice, status: 'refunded' })).toBe(false);
  });

  it('carga las opciones de turno del hotel al inicializar y las muestra en el select de auditoría', () => {
    const ctx = setup();

    expect(ctx.api.getShiftOptions).toHaveBeenCalledWith(1);
    expect(ctx.component.shiftOptions()).toEqual([{ id: 'shift-1', label: 'morning · Carlos · 09/08 06:00' }]);

    const el = ctx.fixture.nativeElement as HTMLElement;
    const select = el.querySelector('.invl-audit-select') as HTMLSelectElement;
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

  it('limpiar filtros de auditoría remueve turno, cajero y los demás filtros de la URL', () => {
    const ctx = setup();

    ctx.component.clearAllFilters();
    ctx.fixture.detectChanges();

    expect(ctx.router.navigate).toHaveBeenCalledWith([], expect.objectContaining({
      queryParams: expect.objectContaining({ turno: null, cajero: null, status: null, q: null }),
    }));
  });
});
