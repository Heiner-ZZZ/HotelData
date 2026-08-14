import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of, Subject } from 'rxjs';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { AuthService } from '../../../../core/auth/auth.service';
import { BillingApiService } from '../../services/billing-api.service';
import { InvoiceDetailPageComponent } from './invoice-detail-page';

describe('InvoiceDetailPageComponent', () => {
  const invoiceDto = {
    _id: 'INV-1',
    booking_id: 'BK-1',
    invoice_number: 'INV-202608-0001',
    prop_id: 1,
    subtotal: 100,
    taxes: 16,
    total: 116,
    status: 'issued',
    issued_at: '2026-08-09T10:00:00',
    guest_name: 'Test Guest',
    guest_email: 'guest@test.com',
    guest_cedula: '',
    check_in_date: '2026-08-09',
    check_out_date: '2026-08-11',
    total_nights: 2,
    rooms: 1,
    room_type_name: 'Standard',
    room_labels: ['110'],
    line_items: [],
    payments: [],
  };

  function setup(confirmResult = true, hasDownload = true) {
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const auth = {
      hasPermission: jest.fn((code: string) => (code === 'reports.download' ? hasDownload : true)),
      isAuthenticated: () => false,
      sessionLoaded: () => false,
      invalidateSession: jest.fn(),
    } as unknown as AuthService;
    const propertyContext = {
      ready: signal(false),
      singleHotelMode: signal(false),
      currentPropId: signal(1),
      currentCurrency: signal('USD'),
      setProperty: jest.fn(),
      clear: jest.fn(),
    } as unknown as PropertyContextService;
    const api = {
      payInvoice: jest.fn(() => of({ ok: true })),
      cancelInvoice: jest.fn(() => of({})),
      addLineItem: jest.fn(() => of({})),
      removeLineItem: jest.fn(() => of({})),
      createCreditNote: jest.fn(() => of({})),
      repairInvoiceSettlement: jest.fn(() => of({})),
    } as unknown as BillingApiService;
    const confirmDialog = {
      open: jest.fn(() => Promise.resolve(confirmResult)),
      openPrompt: jest.fn(() => Promise.resolve('Motivo de prueba')),
    } as unknown as ConfirmDialogService;

    TestBed.configureTestingModule({
      imports: [InvoiceDetailPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: of(convertToParamMap({ invoiceId: 'INV-1' })),
            queryParamMap: of(convertToParamMap({ prop_id: '1' })),
          },
        },
        { provide: PropertyContextService, useValue: propertyContext },
        { provide: BillingApiService, useValue: api },
        { provide: ConfirmDialogService, useValue: confirmDialog },
        { provide: AuthService, useValue: auth },
      ],
    });

    const fixture = TestBed.createComponent(InvoiceDetailPageComponent);
    fixture.detectChanges();
    return {
      fixture,
      component: fixture.componentInstance,
      http: TestBed.inject(HttpTestingController),
      api,
      confirmDialog,
      auth,
    };
  }

  /** Flush the invoice httpResource (+ the dependent services request) so `invoice()` has a value. */
  async function seedInvoice(ctx: { http: HttpTestingController; fixture: { detectChanges(): void } }) {
    ctx.http.expectOne('/api/billing/invoices/INV-1?prop_id=1').flush(invoiceDto);
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();
    const services = ctx.http.match('/api/billing/services?prop_id=1&booking_id=BK-1');
    if (services.length) {
      services.forEach((req) => req.flush({ categories: [], chargeable: [], all_items: [] }));
      await new Promise<void>((resolve) => setTimeout(resolve, 0));
      ctx.fixture.detectChanges();
    }
  }

  it('no llama al API de pago si el usuario cancela la confirmación', async () => {
    const ctx = setup(false);
    await seedInvoice(ctx);

    await ctx.component.payInvoice();

    expect(ctx.api.payInvoice).not.toHaveBeenCalled();
  });

  it('abre el modal de confirmación global con el monto de la factura', async () => {
    const ctx = setup();
    await seedInvoice(ctx);

    await ctx.component.payInvoice();

    expect(ctx.confirmDialog.open).toHaveBeenCalledWith(expect.objectContaining({
      title: 'Registrar pago',
      message: expect.stringContaining('$116.00'),
      confirmLabel: 'Registrar pago',
      variant: 'warning',
    }));
  });

  it('llama al API con el id de la factura y el hotel cuando se confirma, y muestra el mensaje', async () => {
    const ctx = setup();
    await seedInvoice(ctx);

    await ctx.component.payInvoice();

    expect(ctx.api.payInvoice).toHaveBeenCalledWith('INV-1', 1);
    expect(ctx.component.actionMessage()).toBe('Pago procesado exitosamente.');
  });

  it('no llama al API de anulación si el usuario cancela la confirmación', async () => {
    const ctx = setup();
    await seedInvoice(ctx);
    (ctx.confirmDialog.openPrompt as jest.Mock).mockResolvedValueOnce(null);

    await ctx.component.cancelInvoice();

    expect(ctx.api.cancelInvoice).not.toHaveBeenCalled();
  });

  it('abre el modal de anulación con un campo de motivo', async () => {
    const ctx = setup();
    await seedInvoice(ctx);

    await ctx.component.cancelInvoice();

    expect(ctx.confirmDialog.openPrompt).toHaveBeenCalledWith(expect.objectContaining({
      title: 'Anular factura',
      variant: 'danger',
      mode: 'delete',
      input: expect.objectContaining({ label: 'Motivo de la anulación (opcional)' }),
    }));
  });

  it('llama al API de anulación con el id, el hotel y el motivo cuando se confirma', async () => {
    const ctx = setup();
    await seedInvoice(ctx);
    (ctx.confirmDialog.openPrompt as jest.Mock).mockResolvedValueOnce('Factura duplicada');

    await ctx.component.cancelInvoice();

    expect(ctx.api.cancelInvoice).toHaveBeenCalledWith('INV-1', 1, 'Factura duplicada');
    expect(ctx.component.actionMessage()).toBe('Factura anulada correctamente.');
  });

  it('muestra el chip de turno/empleado en el historial de pagos', async () => {
    const ctx = setup();
    const dto = {
      ...invoiceDto,
      payments: [
        {
          _id: 'PAY-1',
          booking_id: 'BK-1',
          invoice_id: 'INV-1',
          amount: 50,
          method: 'cash',
          status: 'confirmed',
          reference: 'REF-1',
          paid_at: '2026-08-09T10:00:00',
          shift_id: 'shift-1',
          shift_employee: 'Carlos Pérez',
          shift_opened_by: 'gerente1',
          shift_type: 'morning',
        },
      ],
    };
    ctx.http.expectOne('/api/billing/invoices/INV-1?prop_id=1').flush(dto);
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();
    const services = ctx.http.match('/api/billing/services?prop_id=1&booking_id=BK-1');
    if (services.length) {
      services.forEach((req) => req.flush({ categories: [], chargeable: [], all_items: [] }));
      await new Promise<void>((resolve) => setTimeout(resolve, 0));
      ctx.fixture.detectChanges();
    }

    const el = ctx.fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Carlos Pérez');
    const chip = el.querySelector('.inv-shift-chip');
    expect(chip).not.toBeNull();
    expect(chip?.getAttribute('title')).toContain('shift-1');
    expect(chip?.getAttribute('title')).toContain('morning');
    // El turno (tipo) se muestra junto al empleado para que la impresión/PDF
    // lleve ambos: responsable + turno.
    expect(chip?.textContent).toContain('Matutino');
  });

  it('traduce el tipo de turno a su etiqueta humana', () => {
    const ctx = setup();
    expect(ctx.component.shiftTypeLabel('morning')).toBe('Matutino');
    expect(ctx.component.shiftTypeLabel('afternoon')).toBe('Vespertino');
    expect(ctx.component.shiftTypeLabel('evening')).toBe('Nocturno');
    expect(ctx.component.shiftTypeLabel(null)).toBe('');
  });

  it('no muestra chip de turno en pagos sin atribución', async () => {
    const ctx = setup();
    await seedInvoice(ctx);

    const el = ctx.fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.inv-shift-chip')).toBeNull();
  });

  it('oculta el botón Descargar PDF sin reports.download', async () => {
    const ctx = setup(true, false);
    await seedInvoice(ctx);

    expect(ctx.component.canExport()).toBe(false);
    const el = ctx.fixture.nativeElement as HTMLElement;
    expect(el.textContent).not.toContain('Descargar PDF');
  });

  it('muestra el botón Descargar PDF con reports.download', async () => {
    const ctx = setup(true, true);
    await seedInvoice(ctx);

    expect(ctx.component.canExport()).toBe(true);
    const el = ctx.fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Descargar PDF');
  });

  it('consulta el permiso reports.download en hasPermission', () => {
    const ctx = setup();

    void ctx.component.canExport();
    expect(ctx.auth.hasPermission).toHaveBeenCalledWith('reports.download');
  });
});
