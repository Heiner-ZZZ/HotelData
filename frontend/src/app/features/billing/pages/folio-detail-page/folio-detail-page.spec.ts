import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of } from 'rxjs';

import { FolioDetailPageComponent } from './folio-detail-page';

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

  function setup() {
    const router = { events: of(), navigate: jest.fn() } as unknown as Router;

    TestBed.configureTestingModule({
      imports: [FolioDetailPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: of(convertToParamMap({ bookingId: 'BK-FOLIO' })),
          },
        },
      ],
    });

    const fixture = TestBed.createComponent(FolioDetailPageComponent);
    fixture.detectChanges();
    return {
      fixture,
      component: fixture.componentInstance,
      http: TestBed.inject(HttpTestingController),
    };
  }

  /** Flush the folio + categories httpResources so `folio()` has a value. */
  async function seedFolio(ctx: { http: HttpTestingController; fixture: { detectChanges(): void } }, dto: unknown = folioDto) {
    ctx.http.expectOne('/api/billing/folios/BK-FOLIO').flush(dto);
    ctx.http.expectOne('/api/billing/folios/categories').flush([]);
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();
  }

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

  it('muestra el turno de apertura del folio (created_shift) en la información', async () => {
    const ctx = setup();
    await seedFolio(ctx);

    const el = ctx.fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('Ana Recepción');
    expect(el.textContent).toContain('Matutino (08:00-16:00)');
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
});
