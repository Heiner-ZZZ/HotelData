import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { MarketingApiService } from '../../services/marketing-api.service';
import { PromotionsPageComponent } from './promotions-page';

describe('PromotionsPageComponent', () => {
  function setup() {
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const propertyContext = {
      ready: signal(false),
      singleHotelMode: signal(false),
      currentPropId: signal(1),
      currentPropLabel: signal('Hotel Test'),
      setProperty: jest.fn(),
      clear: jest.fn(),
    } as unknown as PropertyContextService;
    const api = {
      sendPromotion: jest.fn(),
      cancelPromotion: jest.fn(),
    } as unknown as MarketingApiService;
    const confirmDialog = { open: jest.fn(() => Promise.resolve(true)) } as unknown as ConfirmDialogService;

    TestBed.configureTestingModule({
      imports: [PromotionsPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: { queryParamMap: of(convertToParamMap({ prop_id: '1' })) },
        },
        { provide: PropertyContextService, useValue: propertyContext },
        { provide: MarketingApiService, useValue: api },
        { provide: ConfirmDialogService, useValue: confirmDialog },
      ],
    });

    const fixture = TestBed.createComponent(PromotionsPageComponent);
    fixture.detectChanges();
    return {
      fixture,
      component: fixture.componentInstance,
      toast: TestBed.inject(ToastService),
      http: TestBed.inject(HttpTestingController),
      api,
      confirmDialog,
    };
  }

  /** Resolve the estimate httpResource with the given count. */
  function seedEstimate(
    ctx: { http: HttpTestingController },
    count: number,
  ) {
    ctx.http.expectOne('/api/notifications/promotions/estimate?prop_id=1').flush({
      count,
      prop_id: 1,
      notification_type: 'guest_promotional',
    });
  }

  /** Resolve the options httpResource (rate plans + coupon campaigns). */
  function seedOptions(
    ctx: { http: HttpTestingController },
    plans: unknown[] = [],
    campaigns: unknown[] = [],
  ) {
    ctx.http.expectOne('/api/notifications/promotions/options?prop_id=1').flush({
      prop_id: 1,
      rate_plans: plans,
      campaigns,
    });
  }

  /** Resolve the history httpResource with the given items (default empty).
   *  The URL carries &prop_id=1 because the mock route resolves prop_id=1.
   *  ``total`` defaults to the number of items, but can be overridden to
   *  simulate pagination (backend reports more campaigns than the page shows). */
  function seedHistory(
    ctx: { http: HttpTestingController },
    items: unknown[] = [],
    total?: number,
  ) {
    ctx.http.expectOne('/api/notifications/promotions/history?page=1&page_size=20&prop_id=1').flush({
      items,
      total: total ?? items.length,
      page: 1,
      page_size: 20,
      total_pages: items.length ? 1 : 1,
    });
  }

  /** Flush all mount-time requests so whenStable() can resolve. */
  async function seedBoth(
    ctx: { http: HttpTestingController; fixture: { detectChanges(): void; whenStable(): Promise<void> } },
    count: number,
    historyItems: unknown[] = [],
    historyTotal?: number,
    plans: unknown[] = [],
    campaigns: unknown[] = [],
  ) {
    seedEstimate(ctx, count);
    seedOptions(ctx, plans, campaigns);
    seedHistory(ctx, historyItems, historyTotal);
    await ctx.fixture.whenStable();
    ctx.fixture.detectChanges();
  }

  it('fetches the recipient estimate when a hotel is selected', () => {
    const { http } = setup();
    seedEstimate({ http }, 3);
    seedHistory({ http });
  });

  it('requires at least one opted-in recipient to enable the send action', async () => {
    const { fixture } = setup();
    const component = fixture.componentInstance;
    await seedBoth({ http: TestBed.inject(HttpTestingController), fixture }, 0);

    component.title.set('Oferta de verano');
    component.message.set('20% de descuento en tu próxima estadía.');
    fixture.detectChanges();

    expect(component.recipientsCount()).toBe(0);
    expect(component.canSend()).toBe(false);
  });

  it('enables the send action only with a valid title, message and recipients', async () => {
    const { fixture } = setup();
    const component = fixture.componentInstance;
    await seedBoth({ http: TestBed.inject(HttpTestingController), fixture }, 2);

    expect(component.canSend()).toBe(false);

    component.title.set('Oferta');
    component.message.set('Corto');
    fixture.detectChanges();
    expect(component.canSend()).toBe(false);

    component.message.set('20% de descuento en tu próxima estadía.');
    fixture.detectChanges();
    expect(component.canSend()).toBe(true);
  });

  it('sends the promotion through the API after confirmation', async () => {
    const { fixture, api, confirmDialog } = setup();
    const component = fixture.componentInstance;
    await seedBoth({ http: TestBed.inject(HttpTestingController), fixture }, 3);
    api.sendPromotion = jest.fn(() =>
      of({ notification_type: 'guest_promotional', sent: 3, skipped: 0, recipients: ['a@x.com'] }),
    );
    component.title.set('Oferta de verano');
    component.message.set('20% de descuento en tu próxima estadía.');
    fixture.detectChanges();

    await component.reviewAndSend();

    expect(confirmDialog.open).toHaveBeenCalled();
    expect(api.sendPromotion).toHaveBeenCalledWith({
      title: 'Oferta de verano',
      message: '20% de descuento en tu próxima estadía.',
      prop_id: 1,
    });
    expect(component.sentResult()).not.toBeNull();
    expect(component.sentResult()!.sent).toBe(3);
    expect(component.title()).toBe('');
    expect(component.message()).toBe('');
  });

  it('does not send when the user cancels the confirmation', async () => {
    const { fixture, api, confirmDialog } = setup();
    const component = fixture.componentInstance;
    await seedBoth({ http: TestBed.inject(HttpTestingController), fixture }, 1);
    (confirmDialog.open as jest.Mock).mockResolvedValueOnce(false);
    component.title.set('Oferta de verano');
    component.message.set('20% de descuento en tu próxima estadía.');
    fixture.detectChanges();

    await component.reviewAndSend();

    expect(api.sendPromotion).not.toHaveBeenCalled();
    expect(component.sentResult()).toBeNull();
  });

  // ── Historial de envíos ──

  it('carga el historial al montar y muestra fecha, hotel, título y destinatarios', async () => {
    const { fixture } = setup();
    const ctx = { http: TestBed.inject(HttpTestingController), fixture };
    await seedBoth(ctx, 0, [{
      campaign_id: 'PROMO-1-ABC123',
      title: 'Oferta de verano',
      message: '20% de descuento en tu próxima estadía.',
      prop_id: 1,
      hotel_name: 'Hotel Lima Centro',
      sent_at_iso: '2026-08-13T10:00:00Z',
      recipient_count: 3,
      recipients: ['a@x.com', 'b@x.com', 'c@x.com'],
      email_sent: 3,
    }]);

    const component = fixture.componentInstance;
    expect(component.historyItems()).toHaveLength(1);
    expect(component.historyItems()[0].recipient_count).toBe(3);

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Oferta de verano');
    expect(text).toContain('Hotel Lima Centro');
    expect(text).toContain('2026');
  });

  it('filtra el historial por el hotel seleccionado (chip de scope + prop_id en la URL)', async () => {
    const { fixture } = setup();
    const http = TestBed.inject(HttpTestingController);

    // Con prop_id=1 en la URL, el historial pide ?prop_id=1 y muestra el chip.
    await seedBoth({ http, fixture }, 0, [
      {
        campaign_id: 'PROMO-1-ABC123',
        title: 'Oferta de verano',
        message: '20% de descuento en tu próxima estadía.',
        prop_id: 1,
        hotel_name: 'Hotel Lima Centro',
        sent_at_iso: '2026-08-13T10:00:00Z',
        recipient_count: 3,
        recipients: ['a@x.com', 'b@x.com', 'c@x.com'],
        email_sent: 3,
      },
    ]);

    const component = fixture.componentInstance;
    expect(component.historyScopeLabel()).toBe('Hotel Test');
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Hotel Test'); // chip del scope en el panel
    expect(text).toContain('Oferta de verano');
  });

  it('muestra el total de campañas del hotel en el chip de scope (del backend, no de las filas)', async () => {
    const { fixture } = setup();
    const http = TestBed.inject(HttpTestingController);
    // La página muestra 2 items, pero el backend reporta 7 campañas en el hotel.
    await seedBoth(
      { http, fixture },
      0,
      [SENT_ITEM, { ...SENT_ITEM, campaign_id: 'PROMO-1-DEF456' }],
      7,
    );

    const component = fixture.componentInstance;
    expect(component.historyTotal()).toBe(7);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Hotel Test'); // chip de scope
    expect(text).toContain('7'); // contador de campañas en el chip
    // La palabra «campañas» vive en la semántica accesible del chip (no en
    // el texto visible, que es una píldora compacta con solo el número).
    const chip = (fixture.nativeElement as HTMLElement).querySelector('.promo-history-scope');
    expect(chip?.getAttribute('aria-label')).toBe('7 campañas en Hotel Test');
    expect(chip?.getAttribute('title')).toBe('7 campañas en Hotel Test');
  });

  it('recarga el historial tras un envío exitoso', async () => {
    const { fixture, api } = setup();
    const component = fixture.componentInstance;
    const http = TestBed.inject(HttpTestingController);
    await seedBoth({ http, fixture }, 3);

    api.sendPromotion = jest.fn(() =>
      of({ notification_type: 'guest_promotional', sent: 3, skipped: 0, recipients: ['a@x.com'] }),
    );
    component.title.set('Oferta de verano');
    component.message.set('20% de descuento en tu próxima estadía.');
    fixture.detectChanges();

    await component.reviewAndSend();

    // Tras el envío el historial se recarga: reload() re-dispara el GET
    // en el siguiente ciclo de change detection (efecto del httpResource).
    expect(api.sendPromotion).toHaveBeenCalled();
    fixture.detectChanges();
    seedHistory({ http }, []);
    await fixture.whenStable();
    fixture.detectChanges();

    expect(component.sentResult()?.sent).toBe(3);
  });

  // ── Programación de envíos (send_at + cola) ──

  it('programa la promoción cuando hay una fecha futura', async () => {
    const { fixture, api, confirmDialog } = setup();
    const component = fixture.componentInstance;
    await seedBoth({ http: TestBed.inject(HttpTestingController), fixture }, 3);
    api.sendPromotion = jest.fn(() =>
      of({
        notification_type: 'guest_promotional',
        sent: 0,
        skipped: 0,
        recipients: [],
        scheduled: true,
        campaign_id: 'PROMO-1-ABCD1234',
        send_at_iso: '2026-08-20T15:00:00.000Z',
      }),
    );
    component.title.set('Oferta de verano');
    component.message.set('20% de descuento en tu próxima estadía.');
    const localInput = '2026-08-20T10:00';
    component.scheduleAt.set(localInput);
    fixture.detectChanges();

    expect(component.isScheduled()).toBe(true);
    await component.reviewAndSend();

    expect(confirmDialog.open).toHaveBeenCalled();
    expect(api.sendPromotion).toHaveBeenCalledWith({
      title: 'Oferta de verano',
      message: '20% de descuento en tu próxima estadía.',
      prop_id: 1,
      send_at: new Date(localInput).toISOString(),
    });
    expect(component.sentResult()?.scheduled).toBe(true);
    expect(component.title()).toBe('');
    expect(component.message()).toBe('');
    expect(component.scheduleAt()).toBe('');
  });

  it('envía de inmediato cuando no hay fecha programada', async () => {
    const { fixture, api } = setup();
    const component = fixture.componentInstance;
    await seedBoth({ http: TestBed.inject(HttpTestingController), fixture }, 2);
    api.sendPromotion = jest.fn(() =>
      of({ notification_type: 'guest_promotional', sent: 2, skipped: 0, recipients: ['a@x.com'] }),
    );
    component.title.set('Oferta');
    component.message.set('20% de descuento en tu próxima estadía.');
    component.scheduleAt.set('');
    fixture.detectChanges();

    expect(component.isScheduled()).toBe(false);
    await component.reviewAndSend();

    // Sin fecha el payload no incluye send_at (contrato limpio).
    expect(api.sendPromotion).toHaveBeenCalledWith({
      title: 'Oferta',
      message: '20% de descuento en tu próxima estadía.',
      prop_id: 1,
    });
  });

  it('cancela una promoción programada desde el historial', async () => {
    const { fixture, api } = setup();
    const component = fixture.componentInstance;
    const http = TestBed.inject(HttpTestingController);
    await seedBoth({ http, fixture }, 0, [
      {
        campaign_id: 'PROMO-1-CANCELME',
        title: 'Programada',
        message: 'Promoción futura agendada para mañana.',
        prop_id: 1,
        hotel_name: 'Hotel Test',
        status: 'pending',
        send_at_iso: '2026-08-20T15:00:00.000Z',
        recipient_count: 2,
        recipients: [],
        email_sent: 0,
      },
    ]);

    api.cancelPromotion = jest.fn(() =>
      of({ campaign_id: 'PROMO-1-CANCELME', canceled: true }),
    );

    expect(component.canCancel(component.historyItems()[0])).toBe(true);
    await component.cancelPromotion('PROMO-1-CANCELME');

    expect(api.cancelPromotion).toHaveBeenCalledWith('PROMO-1-CANCELME');
    // Tras cancelar el historial se recarga.
    fixture.detectChanges();
    seedHistory({ http }, []);
    await fixture.whenStable();
    fixture.detectChanges();
    expect(component.historyItems()).toHaveLength(0);
  });

  // ── Detalle de campaña (clic en fila → mensaje completo + destinatarios) ──

  const SENT_ITEM = {
    campaign_id: 'PROMO-1-ABC123',
    title: 'Oferta de verano',
    message: '20% de descuento en tu próxima estadía reservando antes del 30 de septiembre.',
    prop_id: 1,
    hotel_name: 'Hotel Lima Centro',
    sent_at_iso: '2026-08-13T10:00:00Z',
    recipient_count: 2,
    recipients: ['a@x.com', 'b@x.com'],
    email_sent: 2,
    status: 'sent',
  };

  const RECIPIENTS_DTO = {
    campaign_id: 'PROMO-1-ABC123',
    title: 'Oferta de verano',
    message: '20% de descuento en tu próxima estadía reservando antes del 30 de septiembre.',
    prop_id: 1,
    hotel_name: 'Hotel Lima Centro',
    status: 'sent',
    sent_at_iso: '2026-08-13T10:00:00Z',
    recipient_count: 2,
    email_sent: 2,
    recipients: [
      { email: 'a@x.com', name: 'Ana', is_read: true, read_at_iso: '2026-08-13T11:00:00Z' },
      { email: 'b@x.com', name: 'Bruno', is_read: false, read_at_iso: null },
    ],
  };

  async function openDetailAndFlush(
    ctx: { http: HttpTestingController; fixture: { detectChanges(): void; whenStable(): Promise<void>; nativeElement: HTMLElement } },
  ) {
    const row = ctx.fixture.nativeElement.querySelector('.promo-history-row');
    expect(row).not.toBeNull();
    (row as HTMLElement).click();
    ctx.fixture.detectChanges();
    TestBed.flushEffects();
    ctx.http.expectOne('/api/notifications/promotions/PROMO-1-ABC123/recipients').flush(RECIPIENTS_DTO);
    await ctx.fixture.whenStable();
    TestBed.flushEffects();
    ctx.fixture.detectChanges();
  }

  it('abre el detalle con el mensaje completo y los destinatarios al hacer clic en una fila', async () => {
    const { fixture } = setup();
    const component = fixture.componentInstance;
    const http = TestBed.inject(HttpTestingController);
    await seedBoth({ http, fixture }, 0, [SENT_ITEM]);

    await openDetailAndFlush({ http, fixture });

    expect(component.detailCampaign()?.campaign_id).toBe('PROMO-1-ABC123');
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    // Mensaje completo (sin clamp) dentro del detalle.
    expect(text).toContain('Oferta de verano');
    expect(text).toContain('20% de descuento en tu próxima estadía reservando antes del 30 de septiembre.');
    // Destinatarios con nombre, email y estado de lectura.
    expect(text).toContain('Ana');
    expect(text).toContain('a@x.com');
    expect(text).toContain('Leída');
    expect(text).toContain('Bruno');
    expect(text).toContain('b@x.com');
    expect(text).toContain('Sin leer');
  });

  it('cierra el detalle con el botón de cerrar', async () => {
    const { fixture } = setup();
    const component = fixture.componentInstance;
    const http = TestBed.inject(HttpTestingController);
    await seedBoth({ http, fixture }, 0, [SENT_ITEM]);

    await openDetailAndFlush({ http, fixture });
    expect(component.detailCampaign()).not.toBeNull();

    const closeBtn = (fixture.nativeElement as HTMLElement).querySelector('.promo-detail-close');
    expect(closeBtn).not.toBeNull();
    (closeBtn as HTMLElement).click();
    fixture.detectChanges();

    expect(component.detailCampaign()).toBeNull();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).not.toContain('Destinatarios');
  });

  it('muestra el estado "aún no se ha enviado" para una campaña programada', async () => {
    const { fixture } = setup();
    const http = TestBed.inject(HttpTestingController);
    await seedBoth({ http, fixture }, 0, [
      {
        campaign_id: 'PROMO-1-PENDING',
        title: 'Programada',
        message: 'Promoción futura agendada para mañana.',
        prop_id: 1,
        hotel_name: 'Hotel Test',
        status: 'pending',
        send_at_iso: '2026-08-20T15:00:00.000Z',
        recipient_count: 2,
        recipients: [],
        email_sent: 0,
      },
    ]);
    fixture.detectChanges();
    TestBed.flushEffects();
    const row = (fixture.nativeElement as HTMLElement).querySelector('.promo-history-row');
    expect(row).not.toBeNull();
    (row as HTMLElement).click();
    fixture.detectChanges();
    TestBed.flushEffects();
    http.expectOne('/api/notifications/promotions/PROMO-1-PENDING/recipients').flush({
      campaign_id: 'PROMO-1-PENDING',
      title: 'Programada',
      message: 'Promoción futura agendada para mañana.',
      prop_id: 1,
      hotel_name: 'Hotel Test',
      status: 'pending',
      send_at_iso: '2026-08-20T15:00:00.000Z',
      recipient_count: 2,
      email_sent: 0,
      recipients: [],
    });
    await fixture.whenStable();
    TestBed.flushEffects();
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Aún no se ha enviado');
    expect(text).toContain('2 destinatarios estimados');
  });

  // ── Fase 2: detalles de la oferta (applies_to tarifas + cupones) ──

  it('pide las opciones de planes tarifarios del hotel seleccionado', () => {
    const { http } = setup();
    seedEstimate({ http }, 3);
    seedOptions({ http }, [
      { rate_plan_id: 'RP-1-deluxe', name: 'Deluxe', room_type_labels: ['Deluxe King'] },
    ]);
    seedHistory({ http });
  });

  it('incluye los detalles de la oferta (Fase 2) en el payload al enviar', async () => {
    const { fixture, api } = setup();
    const component = fixture.componentInstance;
    const http = TestBed.inject(HttpTestingController);
    await seedBoth({ http, fixture }, 3);
    api.sendPromotion = jest.fn(() =>
      of({
        notification_type: 'guest_promotional',
        sent: 3,
        skipped: 0,
        recipients: ['a@x.com'],
        promotion_id: 'OFFER-1-ABC123',
      }),
    );
    component.title.set('Oferta de verano');
    component.message.set('20% de descuento en tu próxima estadía.');
    component.publicMessage.set('20% de descuento en tarifas Deluxe reservando directo.');
    component.validityStart.set('2026-08-01');
    component.validityEnd.set('2026-09-30');
    component.segment.set('families');
    component.couponMode.set('create');
    component.promoCode.set('verano20');
    component.discountPercent.set(20);
    fixture.detectChanges();

    expect(component.hasOfferDetails()).toBe(true);
    await component.reviewAndSend();

    expect(api.sendPromotion).toHaveBeenCalledWith({
      title: 'Oferta de verano',
      message: '20% de descuento en tu próxima estadía.',
      prop_id: 1,
      public_message: '20% de descuento en tarifas Deluxe reservando directo.',
      validity_start: '2026-08-01',
      validity_end: '2026-09-30',
      segment: 'families',
      applies_to_scope: 'property',
      promo_code: 'verano20',
      discount_percent: 20,
    });
  });

  it('bloquea el envío cuando hay código promocional sin descuento válido', async () => {
    const { fixture } = setup();
    const component = fixture.componentInstance;
    await seedBoth({ http: TestBed.inject(HttpTestingController), fixture }, 2);

    component.title.set('Oferta de verano');
    component.message.set('20% de descuento en tu próxima estadía.');
    component.couponMode.set('create');
    component.promoCode.set('VERANO20');
    fixture.detectChanges();

    expect(component.promoCodeInvalid()).toBe(true);
    expect(component.canSend()).toBe(false);

    component.discountPercent.set(20);
    fixture.detectChanges();
    expect(component.promoCodeInvalid()).toBe(false);
    expect(component.canSend()).toBe(true);
  });

  it('aplica la oferta a planes tarifarios seleccionados (applies_to + payload)', async () => {
    const { fixture, api } = setup();
    const component = fixture.componentInstance;
    const http = TestBed.inject(HttpTestingController);
    const plans = [
      { rate_plan_id: 'RP-1-deluxe', name: 'Deluxe', room_type_labels: [] },
      { rate_plan_id: 'RP-1-king', name: 'King', room_type_labels: ['King Suite'] },
    ];
    await seedBoth({ http, fixture }, 2, [], 0, plans);
    api.sendPromotion = jest.fn(() =>
      of({ notification_type: 'guest_promotional', sent: 2, skipped: 0, recipients: ['a@x.com'] }),
    );
    component.title.set('Oferta');
    component.message.set('20% de descuento en tu próxima estadía.');
    component.appliesToScope.set('rate_plans');
    component.togglePlan('RP-1-deluxe');
    component.togglePlan('RP-1-king');
    fixture.detectChanges();

    expect(component.appliesToLabel()).toBe('Deluxe, King');
    await component.reviewAndSend();

    expect(api.sendPromotion).toHaveBeenCalledWith({
      title: 'Oferta',
      message: '20% de descuento en tu próxima estadía.',
      prop_id: 1,
      segment: 'all',
      applies_to_scope: 'rate_plans',
      rate_plan_ids: ['RP-1-deluxe', 'RP-1-king'],
    });
  });

  it('mantiene la conversión del descuento sin depender de globales en la plantilla', () => {
    const { component } = setup();

    expect(component.parseDiscount('20')).toBe(20);
    expect(component.parseDiscount('')).toBeNull();
    expect(component.parseDiscount('no-es-un-numero')).toBeNull();
  });

  // ── Vínculo de campaña de cupones existente de Tarifas (Opción A) ──

  const CAMPAIGN = {
    campaign_id: 'PC-1-luna-de-miel',
    name: 'Luna de miel',
    discount_percent: 15,
    coupon_code: 'LUNA15',
    is_active: true,
  };

  it('vincula una campaña de cupones existente de Tarifas sin crear una nueva', async () => {
    const { fixture, api } = setup();
    const component = fixture.componentInstance;
    const http = TestBed.inject(HttpTestingController);
    await seedBoth({ http, fixture }, 3, [], 0, [], [CAMPAIGN]);
    api.sendPromotion = jest.fn(() =>
      of({ notification_type: 'guest_promotional', sent: 3, skipped: 0, recipients: ['a@x.com'] }),
    );
    component.title.set('Oferta');
    component.message.set('20% de descuento en tu próxima estadía.');
    component.couponMode.set('link');
    component.linkedCampaignId.set('PC-1-luna-de-miel');
    fixture.detectChanges();

    expect(component.couponPreview()?.code).toBe('LUNA15');
    expect(component.couponPreview()?.discount).toBe(15);
    expect(component.couponInvalid()).toBe(false);
    expect(component.canSend()).toBe(true);

    await component.reviewAndSend();

    expect(api.sendPromotion).toHaveBeenCalledWith({
      title: 'Oferta',
      message: '20% de descuento en tu próxima estadía.',
      prop_id: 1,
      segment: 'all',
      applies_to_scope: 'property',
      coupon_campaign_id: 'PC-1-luna-de-miel',
    });
  });

  it('bloquea el envío en modo vincular sin campaña seleccionada', async () => {
    const { fixture } = setup();
    const component = fixture.componentInstance;
    const http = TestBed.inject(HttpTestingController);
    await seedBoth({ http, fixture }, 2, [], 0, [], [CAMPAIGN]);
    component.title.set('Oferta');
    component.message.set('20% de descuento en tu próxima estadía.');
    component.couponMode.set('link');
    fixture.detectChanges();

    expect(component.couponInvalid()).toBe(true);
    expect(component.canSend()).toBe(false);
  });

  it('al cambiar de modo de cupón se limpian los campos del otro modo', () => {
    const { component } = setup();

    component.couponMode.set('create');
    component.promoCode.set('VERANO20');
    component.discountPercent.set(20);
    component.setCouponMode('link');
    expect(component.promoCode()).toBe('');
    expect(component.discountPercent()).toBeNull();

    component.linkedCampaignId.set('PC-1-luna-de-miel');
    component.setCouponMode('create');
    expect(component.linkedCampaignId()).toBe('');
  });

  // ── Manejo del conflicto «el código ya existe en otra campaña» ──

  const CONFLICT_ERROR = {
    status: 400,
    message: 'El código LUNA15 ya existe en la campaña «Luna de miel» de Tarifas. Vincúlala en lugar de crear una nueva.',
    details: {
      detail: {
        message: 'El código LUNA15 ya existe en la campaña «Luna de miel» de Tarifas. Vincúlala en lugar de crear una nueva.',
        code: 'COUPON_CODE_EXISTS',
        campaign_id: 'PC-1-luna-de-miel',
        campaign_name: 'Luna de miel',
        coupon_code: 'LUNA15',
      },
    },
  };

  it('muestra el conflicto del backend como banner destacado y permite vincular la campaña', async () => {
    const { fixture, api } = setup();
    const component = fixture.componentInstance;
    const http = TestBed.inject(HttpTestingController);
    await seedBoth({ http, fixture }, 2, [], 0, [], [CAMPAIGN]);
    api.sendPromotion = jest.fn(() => throwError(() => CONFLICT_ERROR));
    component.title.set('Oferta');
    component.message.set('20% de descuento en tu próxima estadía.');
    component.couponMode.set('create');
    component.promoCode.set('LUNA15');
    component.discountPercent.set(15);
    fixture.detectChanges();

    await component.reviewAndSend();
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    const banner = el.querySelector('.promo-coupon-conflict');
    expect(banner).not.toBeNull();
    expect(banner?.textContent).toContain('Luna de miel');

    const linkBtn = banner?.querySelector('.promo-coupon-conflict-link');
    expect(linkBtn).not.toBeNull();
    (linkBtn as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(component.couponMode()).toBe('link');
    expect(component.linkedCampaignId()).toBe('PC-1-luna-de-miel');
    expect(component.couponConflict()).toBeNull();
    expect(component.activeConflict()).toBeNull();
  });

  it('descarta el banner de conflicto reactivo con el botón de cerrar', async () => {
    const { fixture, api } = setup();
    const component = fixture.componentInstance;
    const http = TestBed.inject(HttpTestingController);
    await seedBoth({ http, fixture }, 2, [], 0, [], [CAMPAIGN]);
    api.sendPromotion = jest.fn(() => throwError(() => CONFLICT_ERROR));
    component.title.set('Oferta');
    component.message.set('20% de descuento en tu próxima estadía.');
    component.couponMode.set('create');
    component.promoCode.set('LUNA15');
    component.discountPercent.set(15);
    fixture.detectChanges();

    await component.reviewAndSend();
    fixture.detectChanges();
    expect(component.activeConflict()).not.toBeNull();

    const el = fixture.nativeElement as HTMLElement;
    const dismiss = el.querySelector('.promo-coupon-conflict-dismiss');
    expect(dismiss).not.toBeNull();
    (dismiss as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(component.activeConflict()).toBeNull();
  });

  it('los errores genéricos de envío siguen usando el toast y no muestran el banner', async () => {
    const { fixture, api, toast } = setup();
    const component = fixture.componentInstance;
    const http = TestBed.inject(HttpTestingController);
    await seedBoth({ http, fixture }, 2);
    const toastSpy = jest.spyOn(toast, 'error');
    api.sendPromotion = jest.fn(() =>
      throwError(() => ({ status: 500, message: 'Error interno del servidor.', details: {} })),
    );
    component.title.set('Oferta');
    component.message.set('20% de descuento en tu próxima estadía.');
    component.couponMode.set('create');
    component.promoCode.set('VERANO20');
    component.discountPercent.set(20);
    fixture.detectChanges();

    await component.reviewAndSend();
    fixture.detectChanges();

    expect(toastSpy).toHaveBeenCalledWith('Error interno del servidor.');
    expect(component.activeConflict()).toBeNull();
    expect(
      (fixture.nativeElement as HTMLElement).querySelector('.promo-coupon-conflict'),
    ).toBeNull();
  });

  it('detecta proactivamente un código que ya es el cupón de una campaña del hotel', async () => {
    const { fixture } = setup();
    const component = fixture.componentInstance;
    const http = TestBed.inject(HttpTestingController);
    await seedBoth({ http, fixture }, 2, [], 0, [], [CAMPAIGN]);

    component.couponMode.set('create');
    component.promoCode.set('luna15'); // minúsculas → se compara normalizado
    component.discountPercent.set(15);
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    const banner = el.querySelector('.promo-coupon-conflict');
    expect(banner).not.toBeNull();
    expect(banner?.textContent).toContain('Luna de miel');

    // Al cambiar el código, el aviso desaparece (ya no colisiona).
    component.promoCode.set('VERANO20');
    fixture.detectChanges();
    expect(component.activeConflict()).toBeNull();

    // Si vuelve a colisionar, el botón vincula la campaña directamente.
    component.promoCode.set('luna15');
    fixture.detectChanges();
    const linkBtn = el.querySelector(
      '.promo-coupon-conflict-link',
    ) as HTMLButtonElement;
    linkBtn.click();
    fixture.detectChanges();

    expect(component.couponMode()).toBe('link');
    expect(component.linkedCampaignId()).toBe('PC-1-luna-de-miel');
    expect(component.activeConflict()).toBeNull();
  });

  // ── Edición + pausa/reactivación de la oferta pública (Fase 3) ──

  const ACTIVE_OFFER = {
    ...SENT_ITEM,
    offer_status: 'active',
    public_message: '20% de descuento en tarifas Deluxe reservando directo.',
    validity: { start_date: '2026-08-01', end_date: '2026-09-30' },
    applies_to: { scope: 'property', rate_plan_ids: [] },
    segment: { audience: 'families' },
    promo_code: 'VERANO20',
    discount_percent: 20,
  };

  const PAUSED_OFFER = {
    ...SENT_ITEM,
    campaign_id: 'PROMO-1-PAUSED',
    title: 'Oferta pausada',
    offer_status: 'paused',
  };

  it('expone acciones de oferta según el estado y el badge de pausa', async () => {
    const { fixture } = setup();
    const component = fixture.componentInstance;
    const http = TestBed.inject(HttpTestingController);
    await seedBoth({ http, fixture }, 0, [ACTIVE_OFFER, PAUSED_OFFER]);

    const active = component.historyItems()[0];
    const paused = component.historyItems()[1];
    expect(component.canEditOffer(active)).toBe(true);
    expect(component.canPause(active)).toBe(true);
    expect(component.canResume(active)).toBe(false);
    expect(component.canEditOffer(paused)).toBe(true);
    expect(component.canPause(paused)).toBe(false);
    expect(component.canResume(paused)).toBe(true);

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Pausada'); // badge de pausa en la fila pausada
  });

  it('abre el modal de edición pre-llenado con los campos de la entidad', async () => {
    const { fixture } = setup();
    const component = fixture.componentInstance;
    const http = TestBed.inject(HttpTestingController);
    await seedBoth({ http, fixture }, 0, [ACTIVE_OFFER]);

    component.openEdit(component.historyItems()[0]);
    fixture.detectChanges();
    TestBed.flushEffects();
    // El modal pide las opciones del hotel de la campaña (independiente del selector).
    http.expectOne('/api/notifications/promotions/options?prop_id=1').flush({
      prop_id: 1,
      rate_plans: [
        { rate_plan_id: 'RP-1-deluxe', name: 'Deluxe', room_type_labels: ['Deluxe King'] },
      ],
    });
    await fixture.whenStable();
    TestBed.flushEffects();
    fixture.detectChanges();

    expect(component.editingCampaign()?.campaign_id).toBe('PROMO-1-ABC123');
    expect(component.editPublicMessage()).toBe('20% de descuento en tarifas Deluxe reservando directo.');
    expect(component.editValidityStart()).toBe('2026-08-01');
    expect(component.editValidityEnd()).toBe('2026-09-30');
    expect(component.editSegment()).toBe('families');
    expect(component.editAppliesScope()).toBe('property');
    expect(component.editSelectedPlans()).toEqual([]);

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Editar oferta');
    expect(text).toContain('VERANO20'); // código (solo lectura, vive en Tarifas)
  });

  it('guarda la edición vía updateOffer sin re-enviar y recarga el historial', async () => {
    const { fixture, api } = setup();
    const component = fixture.componentInstance;
    const http = TestBed.inject(HttpTestingController);
    await seedBoth({ http, fixture }, 0, [ACTIVE_OFFER]);

    api.updateOffer = jest.fn(() =>
      of({ campaign_id: 'PROMO-1-ABC123', offer_status: 'active' }),
    );
    component.openEdit(component.historyItems()[0]);
    fixture.detectChanges();
    TestBed.flushEffects();
    http.expectOne('/api/notifications/promotions/options?prop_id=1').flush({ prop_id: 1, rate_plans: [] });
    await fixture.whenStable();
    TestBed.flushEffects();
    fixture.detectChanges();

    component.editPublicMessage.set('Nueva descripción editada.');
    component.editValidityEnd.set('2026-10-31');
    component.editSegment.set('business');
    fixture.detectChanges();

    component.saveEdit();

    expect(api.updateOffer).toHaveBeenCalledWith('PROMO-1-ABC123', {
      public_message: 'Nueva descripción editada.',
      validity_start: '2026-08-01',
      validity_end: '2026-10-31',
      segment: 'business',
      applies_to_scope: 'property',
      rate_plan_ids: [],
    });
    expect(component.editingCampaign()).toBeNull(); // el modal se cierra
    // Tras guardar el historial se recarga.
    fixture.detectChanges();
    seedHistory({ http }, []);
    await fixture.whenStable();
    fixture.detectChanges();
    expect(component.historyItems()).toHaveLength(0);
  });

  it('pausa la oferta activa con confirmación y recarga el historial', async () => {
    const { fixture, api, confirmDialog } = setup();
    const component = fixture.componentInstance;
    const http = TestBed.inject(HttpTestingController);
    await seedBoth({ http, fixture }, 0, [ACTIVE_OFFER]);

    api.setOfferPublic = jest.fn(() =>
      of({ campaign_id: 'PROMO-1-ABC123', offer_status: 'paused', active: false }),
    );

    await component.togglePublic(component.historyItems()[0]);

    expect(confirmDialog.open).toHaveBeenCalled();
    expect(api.setOfferPublic).toHaveBeenCalledWith('PROMO-1-ABC123', false);
    fixture.detectChanges();
    seedHistory({ http }, []);
    await fixture.whenStable();
    fixture.detectChanges();
    expect(component.historyItems()).toHaveLength(0);
  });

  it('reactiva una oferta pausada sin confirmación', async () => {
    const { fixture, api, confirmDialog } = setup();
    const component = fixture.componentInstance;
    const http = TestBed.inject(HttpTestingController);
    await seedBoth({ http, fixture }, 0, [PAUSED_OFFER]);

    api.setOfferPublic = jest.fn(() =>
      of({ campaign_id: 'PROMO-1-PAUSED', offer_status: 'active', active: true }),
    );

    await component.togglePublic(component.historyItems()[0]);

    expect(confirmDialog.open).not.toHaveBeenCalled();
    expect(api.setOfferPublic).toHaveBeenCalledWith('PROMO-1-PAUSED', true);
  });
});
