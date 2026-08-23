import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { BILLING_WRITE_OFF_APPROVE } from '../../../../core/auth/permission.constants';
import { FolioDetailPageComponent } from './folio-detail-page';

const categoriesResponse = [
  { id: 'habitacion', label: 'Habitación', icon: 'bed' },
  { id: 'restaurante', label: 'Restaurante', icon: 'restaurant' },
  { id: 'bar', label: 'Bar', icon: 'local_bar' },
  { id: 'room_service', label: 'Room Service', icon: 'room_service' },
  { id: 'minibar', label: 'Minibar', icon: 'kitchen' },
  { id: 'spa', label: 'Spa', icon: 'spa' },
  { id: 'lavanderia', label: 'Lavandería', icon: 'local_laundry_service' },
  { id: 'parking', label: 'Parking', icon: 'local_parking' },
  { id: 'mascotas', label: 'Mascotas', icon: 'pets' },
  { id: 'llamadas', label: 'Llamadas', icon: 'phone' },
  { id: 'danos', label: 'Daños', icon: 'warning' },
  { id: 'late_checkout', label: 'Late Check-Out', icon: 'schedule' },
  { id: 'early_checkin', label: 'Early Check-In', icon: 'alarm' },
  { id: 'no_show', label: 'No-Show', icon: 'event_busy' },
  { id: 'descuento', label: 'Descuento', icon: 'sell' },
  { id: 'otros', label: 'Otros', icon: 'more_horiz' },
];

describe('FolioDetailPageComponent', () => {
  const folioDto = {
    id: 'folio-1',
    folio_number: 'FL-0001',
    booking_id: 'BK-FOLIO',
    prop_id: 1,
    guest_name: 'Guest Folio',
    guest_email: 'guest@test.com',
    room_label: '110',
    hotel_label: 'Hotel Lima Centro',
    check_in_date: '2026-08-09',
    check_out_date: '2026-08-11',
    status: 'open',
    is_expired: false,
    has_invoice: false,
    total_room: 218,
    total_charges: 50,
    total_discounts: 0,
    total_payments: 0,
    total_due: 268,
    postings: [
      {
        posting_id: 'p1',
        type: 'room',
        category: 'Habitación',
        concept: 'Habitación Standard',
        amount: 218,
        quantity: 2,
        unit_price: 109,
        reference_id: 'r1',
        reference_type: 'booking',
        posted_at: '2026-08-09T10:00:00',
      },
      {
        posting_id: 'p2',
        type: 'payment',
        category: 'Pago',
        concept: 'Pago adelantado',
        amount: 50,
        quantity: 1,
        unit_price: 50,
        reference_id: 'PAY-1',
        reference_type: 'payment',
        posted_at: '2026-08-09T11:00:00',
        shift_id: 'shift-1',
        shift_employee: 'Carlos Pérez',
        shift_opened_by: 'gerente1',
        shift_type: 'morning',
      },
    ],
    posting_count: 2,
    created_at: '2026-08-09T10:00:00',
    closed_at: null,
    closed_by: null,
    reopened_at: null,
    reopened_by: null,
    settlement_type: null,
    settlement_amount: null,
    settlement_reason: null,
    approval_reference: null,
    external_reference: null,
    settled_at: null,
    settled_recorded_at: null,
    settled_by: null,
    settled_by_user_id: null,
    settlement_payment_id: null,
    settlement_payment_ids: [],
    settlement_event_id: null,
    settlement_event_ids: [],
    settlement_shift_id: null,
    settlement_shift_ids: [],
    settlement_invoice_id: null,
    settlement_evidence_type: null,
    settlement_evidence_reference: null,
    invoice_id: null,
    created_shift: {
      shift_id: 'shift-1',
      shift_type: 'morning',
      shift_label: 'Matutino (08:00-16:00)',
      employee: 'Ana Recepción',
      opened_by: 'recep.prueba',
      start_time: '2026-08-09T08:00:00+00:00',
    },
  };

  function setup(options: { canApproveWriteOff?: boolean } = {}) {
    const router = { events: of(), navigate: jest.fn() } as unknown as Router;
    const auth = {
      hasPermission: jest.fn(() => options.canApproveWriteOff ?? true),
    };

    TestBed.configureTestingModule({
      imports: [FolioDetailPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        { provide: AuthService, useValue: auth },
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: of(convertToParamMap({ bookingId: 'BK-FOLIO' })),
            queryParamMap: of(convertToParamMap({ prop_id: '1', prop_label: 'Hotel Lima Centro' })),
            snapshot: { queryParamMap: convertToParamMap({ prop_id: '1', prop_label: 'Hotel Lima Centro' }) },
          },
        },
      ],
    });

    const fixture = TestBed.createComponent(FolioDetailPageComponent);
    fixture.detectChanges();
    return {
      fixture,
      component: fixture.componentInstance,
      auth,
      http: TestBed.inject(HttpTestingController),
    };
  }

  /** Flush the folio + categories httpResources so `folio()` has a value. */
  async function seedFolio(
    ctx: { http: HttpTestingController; fixture: { detectChanges(): void } },
    dto: unknown = folioDto,
    categories: unknown[] = categoriesResponse,
  ) {
    ctx.http.expectOne('/api/billing/folios/BK-FOLIO?prop_id=1').flush(dto);
    ctx.http.expectOne('/api/billing/folios/categories').flush(categories);
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();
  }

  it('usa el label y el icono del catálogo remoto para categorías canónicas', async () => {
    const ctx = setup();
    await seedFolio(ctx, {
      ...folioDto,
      postings: [
        ...folioDto.postings,
        {
          posting_id: 'p3',
          type: 'charge',
          category: 'Etiqueta obsoleta',
          category_id: 'cocktail_lounge',
          concept: 'Consumo de cócteles',
          amount: 35,
          quantity: 1,
          unit_price: 35,
          reference_id: 'CHARGE-1',
          reference_type: 'manual',
          posted_at: '2026-08-09T12:00:00',
        },
      ],
      posting_count: 3,
    }, [{ id: 'cocktail_lounge', label: 'Salón de cócteles', icon: 'local_bar' }]);

    expect(ctx.component.categoryLabel('cocktail_lounge')).toBe('Salón de cócteles');
    expect(ctx.component.categoryIcon('cocktail_lounge')).toBe('local_bar');

    const el = ctx.fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Salón de cócteles');
    expect(Array.from(el.querySelectorAll('.fl-group-icon')).map((icon) => icon.textContent?.trim()))
      .toContain('local_bar');
  });


  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('muestra el chip de turno/empleado en los postings estampados', async () => {
    const ctx = setup();
    await seedFolio(ctx);

    const el = ctx.fixture.nativeElement as HTMLElement;
    const chips = Array.from(el.querySelectorAll('.fl-shift-chip'));
    const paymentChip = chips.find((c) => c.textContent?.includes('Carlos Pérez'));
    expect(paymentChip).toBeDefined();
    expect(paymentChip?.textContent).toContain('Matutino');
    expect(paymentChip?.getAttribute('title')).toContain('shift-1');
  });

  it('el botón Imprimir dispara window.print', async () => {
    const ctx = setup();
    await seedFolio(ctx);
    const printSpy = jest.spyOn(window, 'print').mockImplementation(() => {});

    ctx.component.printPage();

    expect(printSpy).toHaveBeenCalled();
  });

  it('muestra la nota de cargos sin facturar en el comprobante impreso del folio', async () => {
    const ctx = setup();
    await seedFolio(ctx, {
      ...folioDto,
      has_invoice: true,
      invoice_id: 'invoice-1',
      invoice_number: 'INV-001',
      invoice_status: 'issued',
      invoice_subtotal: 218,
      invoice_covered_subtotal: 218,
    });

    const note = ctx.component.reconcileNote();
    expect(note).toEqual({ invoiceNumber: 'INV-001', gap: 50 });

    const noteEl = (ctx.fixture.nativeElement as HTMLElement).querySelector('.fl-reconcile-note');
    expect(noteEl).not.toBeNull();
    expect(noteEl?.classList.contains('fl-reconcile-note--print')).toBe(true);
    expect(noteEl?.getAttribute('role')).toBe('note');
    expect(noteEl?.textContent).toContain('no cubre los cargos adicionales');
    expect(noteEl?.textContent).toContain('$50.00');
    expect(noteEl?.textContent).toContain('factura complementaria');
  });

  it('emite la factura complementaria desde el detalle de Facturación', async () => {
    const ctx = setup();
    await seedFolio(ctx, {
      ...folioDto,
      prop_id: 1,
      has_invoice: true,
      invoice_id: 'invoice-1',
      invoice_number: 'INV-001',
      invoice_status: 'issued',
      invoice_subtotal: 218,
      invoice_covered_subtotal: 218,
    });

    const button = (ctx.fixture.nativeElement as HTMLElement)
      .querySelector('button[data-action="emit-complement"]') as HTMLButtonElement | null;
    expect(button).not.toBeNull();

    button?.click();
    const request = ctx.http.expectOne('/billing/invoices/complement?prop_id=1');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ booking_id: 'BK-FOLIO' });
    expect(request.request.params.get('prop_id')).toBe('1');
    request.flush({ id: 'invoice-2', invoice_number: 'INV-002', status: 'issued', total: 58 });
    ctx.fixture.detectChanges();

    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    const reload = ctx.http.expectOne('/api/billing/folios/BK-FOLIO?prop_id=1');
    reload.flush({
      ...folioDto,
      has_invoice: true,
      invoice_id: 'invoice-1',
      invoice_number: 'INV-001',
      invoice_status: 'issued',
      invoice_subtotal: 218,
      invoice_covered_subtotal: 268,
    });
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();

    expect(ctx.component.actionMessage()).toContain('Factura complementaria INV-002 emitida');
    expect(ctx.component.reconcileNote()).toBeNull();
  });

  it('no muestra la nota impresa cuando la factura cubre el subtotal del folio', async () => {
    const ctx = setup();
    await seedFolio(ctx, {
      ...folioDto,
      has_invoice: true,
      invoice_id: 'invoice-1',
      invoice_number: 'INV-001',
      invoice_status: 'issued',
      invoice_subtotal: 268,
      invoice_covered_subtotal: 268,
    });

    expect(ctx.component.reconcileNote()).toBeNull();
    expect((ctx.fixture.nativeElement as HTMLElement).querySelector('.fl-reconcile-note')).toBeNull();
  });

  it('muestra el turno de apertura del folio (created_shift) en la información', async () => {
    const ctx = setup();
    await seedFolio(ctx);

    const el = ctx.fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Ana Recepción');
    expect(el.textContent).toContain('Matutino (08:00-16:00)');
  });

  it('muestra el posting automático de late check-out con minutos y el icono schedule', async () => {
    const ctx = setup();
    await seedFolio(ctx, {
      ...folioDto,
      total_charges: 75,
      total_due: 293,
      postings: [
        ...folioDto.postings,
        {
          posting_id: 'p3',
          type: 'charge',
          category: 'Late Check-Out',
          category_id: 'late_checkout',
          concept: 'Late check-out autorizado — 150 min después de las 12:00',
          amount: 25,
          quantity: 1,
          unit_price: 25,
          reference_id: 'BK-FOLIO:late_checkout',
          reference_type: 'late_checkout',
          posted_at: '2026-08-10T14:30:00',
        },
      ],
      posting_count: 3,
    });

    const el = ctx.fixture.nativeElement as HTMLElement;
    const text = el.textContent ?? '';
    // Línea 'Late Checkout' con los minutos reales en el concepto.
    expect(text).toContain('Late Check-Out');
    expect(text).toContain('150 min');
    // El posting estandarizado resuelve el icono por el id del catálogo (schedule).
    expect(ctx.component.categoryIcon('late_checkout')).toBe('schedule');
    expect(ctx.component.categoryLabel('late_checkout')).toBe('Late Check-Out');
    // Fallback legado: un posting que solo guarda el label también resuelve.
    expect(ctx.component.categoryIcon('Late check-out')).toBe('schedule');
    const groupIcon = el.querySelector('.fl-group-header .fl-group-icon');
    const scheduleIcons = Array.from(el.querySelectorAll('.fl-group-icon')).filter(
      (i) => i.textContent?.trim() === 'schedule',
    );
    expect(scheduleIcons.length).toBeGreaterThan(0);
    expect(groupIcon).not.toBeNull();
  });

  it('resuelve icono y label por id del catálogo para no-show y early check-in', async () => {
    const ctx = setup();
    await seedFolio(ctx, {
      ...folioDto,
      total_charges: 60,
      total_due: 278,
      postings: [
        ...folioDto.postings,
        {
          posting_id: 'p3',
          type: 'charge',
          category: 'No-Show',
          category_id: 'no_show',
          concept: 'No-show — Penalización del 100% de 1 noche',
          amount: 35,
          quantity: 1,
          unit_price: 35,
          reference_id: 'BK-NS',
          reference_type: 'no_show_penalty',
          posted_at: '2026-08-10T09:00:00',
        },
        {
          posting_id: 'p4',
          type: 'charge',
          category: 'Early Check-In',
          category_id: 'early_checkin',
          concept: 'Early check-in autorizado — 90 min antes',
          amount: 25,
          quantity: 1,
          unit_price: 25,
          reference_id: 'BK-FOLIO:early_check_in',
          reference_type: 'early_check_in',
          posted_at: '2026-08-09T13:30:00',
        },
      ],
      posting_count: 4,
    });

    const el = ctx.fixture.nativeElement as HTMLElement;
    const text = el.textContent ?? '';
    // Labels resueltos del catálogo por id — sin string-matching de labels.
    expect(text).toContain('No-Show');
    expect(text).toContain('Early Check-In');
    expect(ctx.component.categoryIcon('no_show')).toBe('event_busy');
    expect(ctx.component.categoryIcon('early_checkin')).toBe('alarm');
    expect(ctx.component.categoryLabel('no_show')).toBe('No-Show');
    expect(ctx.component.categoryLabel('early_checkin')).toBe('Early Check-In');
    // Fallback legado: labels de postings anteriores al category_id.
    expect(ctx.component.categoryIcon('Penalización')).toBe('event_busy');
    expect(ctx.component.categoryIcon('Early check-in')).toBe('alarm');
    // Ambos grupos renderizan su icono propio (event_busy y alarm).
    const icons = Array.from(el.querySelectorAll('.fl-group-icon')).map(
      (i) => i.textContent?.trim(),
    );
    expect(icons).toContain('event_busy');
    expect(icons).toContain('alarm');
  });

  it('sin atribución no muestra chips ni fila de apertura', async () => {
    const ctx = setup();
    const dto = {
      ...folioDto,
      created_shift: null,
      postings: folioDto.postings.map((p) => ({ ...p, shift_id: undefined, shift_employee: undefined, shift_opened_by: undefined, shift_type: undefined })),
    };
    await seedFolio(ctx, dto);

    const el = ctx.fixture.nativeElement as HTMLElement;
    expect(el.querySelectorAll('.fl-shift-chip').length).toBe(0);
    expect(el.textContent).not.toContain('Ana Recepción');
  });

  it('al intentar cerrar un folio con saldo muestra la instrucción de resolverlo', async () => {
    const ctx = setup();
    await seedFolio(ctx); // total_due: 268 → closeState 'balance_due'

    ctx.component.closeFolio();
    ctx.fixture.detectChanges();

    const el = ctx.fixture.nativeElement as HTMLElement;
    // Criterio de mensaje con acción: además del estado, dice QUÉ hacer.
    expect(el.textContent).toContain('No se puede cerrar');
    expect(el.textContent).toContain('registrá el pago del saldo');
    expect(el.textContent).toContain('write-off / liquidación externa aprobado');
  });

  it('muestra las acciones de excepción cuando el catálogo otorga billing.write_off.approve', async () => {
    const ctx = setup({ canApproveWriteOff: true });
    await seedFolio(ctx);

    const el = ctx.fixture.nativeElement as HTMLElement;
    expect(ctx.auth.hasPermission).toHaveBeenCalledWith(BILLING_WRITE_OFF_APPROVE);
    expect(el.textContent).toContain('Write-off aprobado');
    expect(el.textContent).toContain('Liquidación externa');
    expect(el.textContent).not.toContain('requieren el permiso');
  });

  it('oculta las acciones de excepción sin el permiso del catálogo y orienta a derivar al gerente', async () => {
    const ctx = setup({ canApproveWriteOff: false });
    await seedFolio(ctx);

    const el = ctx.fixture.nativeElement as HTMLElement;
    expect(ctx.component.canApproveWriteOff()).toBe(false);
    expect(el.textContent).not.toContain('Write-off aprobado');
    expect(el.textContent).not.toContain('Liquidación externa');
    expect(el.textContent).toContain('billing.write_off.approve');
    expect(el.textContent).toContain('Derivá el folio al gerente');

    ctx.component.startSettlement('write_off');
    expect(ctx.component.settlementMode()).toBe('idle');
    expect(ctx.component.actionError()).toContain('requiere aprobación del gerente');
  });
});
