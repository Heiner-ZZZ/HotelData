import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { BehaviorSubject, of, Subject } from 'rxjs';

import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { KpiApiService } from '../../../../shared/services/kpi-api.service';
import { RatesApiService } from '../../services/rates-api.service';
import type { CampaignRow } from '../../components/promotions-table/promotions-table';
import { RatesPageComponent, splitCouponsByCampaign } from './rates-page';

describe('splitCouponsByCampaign', () => {
  const coupons = [
    { code: 'A1', activeLabel: 'Sí', campaignId: 'PC-1' },
    { code: 'A2', activeLabel: 'Sí', campaignId: 'PC-1' },
    { code: 'B1', activeLabel: 'No', campaignId: 'PC-2' },
    { code: 'ORF1', activeLabel: 'Sí', campaignId: 'PC-999' }, // campaña inexistente
    { code: 'ORF2', activeLabel: 'Sí', campaignId: '' }, // sin campaign_id
  ];

  it('groups coupons under their campaign keeping order', () => {
    const { byCampaign } = splitCouponsByCampaign(['PC-1', 'PC-2'], coupons);
    expect(byCampaign.get('PC-1')?.map((c) => c.code)).toEqual(['A1', 'A2']);
    expect(byCampaign.get('PC-2')?.map((c) => c.code)).toEqual(['B1']);
  });

  it('isolates coupons whose campaign is unknown or missing as orphans', () => {
    const { orphans } = splitCouponsByCampaign(['PC-1', 'PC-2'], coupons);
    expect(orphans.map((c) => c.code)).toEqual(['ORF1', 'ORF2']);
  });

  it('returns an empty map and no orphans for an empty coupon list', () => {
    const { byCampaign, orphans } = splitCouponsByCampaign(['PC-1'], []);
    expect(byCampaign.size).toBe(0);
    expect(orphans).toEqual([]);
  });
});

describe('RatesPageComponent', () => {
  const promoRow: CampaignRow = {
    campaignId: 'PC-1-verano',
    name: 'Verano',
    description: 'Verano 2026',
    discountPercent: 15,
    isActive: true,
    startDate: '2026-08-01',
    endDate: '2026-12-31',
    couponTotal: 10,
    couponUsed: 0,
    couponAvailable: 10,
    couponDeleted: 0,
    coupons: [],
  };

  function setup(section = 'promos') {
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    // Observable de query params dinámico: permite simular la navegación entre
    // secciones del sidebar (plans ↔ seasons ↔ promos).
    const queryParams = new BehaviorSubject(convertToParamMap({ prop_id: '1', section }));
    const propertyContext = {
      ready: signal(false),
      singleHotelMode: signal(false),
      currentPropId: signal(1),
      currentCurrency: signal('USD'),
      setProperty: jest.fn(),
      clear: jest.fn(),
    } as unknown as PropertyContextService;
    const api = {
      getAmenityCatalog: jest.fn(() => of([])),
      listPropertyPromotions: jest.fn(() => of({ campaigns: [], total: 0 })),
    } as unknown as RatesApiService;
    const kpiApi = {
      getRateTrend: jest.fn(() => of({ dates: [], series: [] })),
    } as unknown as KpiApiService;

    TestBed.configureTestingModule({
      imports: [RatesPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            queryParamMap: queryParams.asObservable(),
          },
        },
        { provide: PropertyContextService, useValue: propertyContext },
        { provide: RatesApiService, useValue: api },
        { provide: KpiApiService, useValue: kpiApi },
      ],
    });

    const fixture = TestBed.createComponent(RatesPageComponent);
    fixture.detectChanges();
    return {
      fixture,
      component: fixture.componentInstance,
      mode: TestBed.inject(OperationModeService),
      toast: TestBed.inject(ToastService),
      http: TestBed.inject(HttpTestingController),
      api,
      queryParams,
      router,
    };
  }

  /** Resolve the rates httpResource so viewState reaches 'success' (promos panel renders). */
  async function seedRates(
    ctx: { http: HttpTestingController; fixture: { detectChanges(): void } },
    rateCoverage: unknown = null,
    ratePlans: unknown[] = [],
    calendarItems: unknown[] = [],
    roomTypes: unknown[] = [],
    minBaseRate?: number,
  ) {
    ctx.http.expectOne('/api/management/rates?prop_id=1').flush({
      prop_id: 1,
      hotel_label: 'Hotel Test',
      room_types: roomTypes,
      rate_plans: ratePlans,
      calendar: calendarItems,
      rate_rules: [],
      promotions: [],
      coupon_codes: [],
      rate_coverage: rateCoverage,
      min_base_rate: minBaseRate,
    });
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();
  }

  function promoPanel(fixture: { nativeElement: HTMLElement }): HTMLElement {
    return fixture.nativeElement.querySelector('.promo-form-panel') as HTMLElement;
  }

  /** Busca un panel surface-card por el texto de su encabezado. */
  function panelByHeading(fixture: { nativeElement: HTMLElement }, heading: string): HTMLElement {
    return Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('section.surface-card'))
      .find((s) => (s.textContent ?? '').includes(heading)) as HTMLElement;
  }

  it('resalta la caja del form de promoción con el color del modo insert al entrar en promos', async () => {
    const ctx = setup();
    await seedRates(ctx);

    const panel = promoPanel(ctx.fixture);
    expect(panel).not.toBeNull();
    expect(ctx.mode.mode()).toBe('insert');
    expect(panel.classList.contains('mode-active')).toBe(true);
    expect(panel.style.getPropertyValue('--op-color')).toContain('--warning');
  });

  it('usa el toast global al cambiar el estado de una promoción (sin toast local)', async () => {
    const ctx = setup();
    await seedRates(ctx);
    const pending = new Subject<unknown>();
    (ctx.api as unknown as { togglePromotion: jest.Mock }).togglePromotion = jest.fn(() => pending);

    ctx.component.onTogglePromo('PC-1-verano');
    pending.next({});
    pending.complete();

    expect(ctx.toast.toasts().some(
      (t) => t.message === 'Estado de promoción actualizado' && t.type === 'success',
    )).toBe(true);
  });

  it('envía los mensajes del form de promoción al toast global', () => {
    const { component, toast } = setup();

    component.onPromoMessage('Promoción creada');
    expect(toast.toasts().some((t) => t.message === 'Promoción creada' && t.type === 'success')).toBe(true);

    component.onPromoError('Error del backend');
    expect(toast.toasts().some((t) => t.message === 'Error del backend' && t.type === 'error')).toBe(true);
  });

  it('nunca renderiza banners .notification ni .message locales (migrado al toast global)', async () => {
    const ctx = setup('promos');
    await seedRates(ctx);

    const banner = (ctx.fixture.nativeElement as HTMLElement).querySelector('.notification, .message');
    expect(banner).toBeNull();
    // El toast global sí está disponible para los mensajes de la página.
    expect(ctx.toast).toBeDefined();
  });

  it('muestra el banner de noches sin tarifa en el overview con el conteo exacto', async () => {
    const ctx = setup('overview');
    await seedRates(ctx, {
      rate_last_date: '2026-07-25',
      inventory_last_date: '2026-10-22',
      gap_nights: 89,
      gap_start: '2026-07-26',
      gap_end: '2026-10-22',
    });

    const banner = (ctx.fixture.nativeElement as HTMLElement).querySelector('.rate-gap-banner') as HTMLElement;
    expect(banner).not.toBeNull();
    expect(banner.textContent).toContain('89');
    expect(banner.textContent).toContain('noches sin tarifa');
    expect(banner.textContent).toContain('Ir a Generar calendario');
    expect(banner.getAttribute('role')).toBe('alert');
  });

  it('no muestra el banner cuando el horizonte de tarifas cubre el inventario', async () => {
    const ctx = setup('overview');
    await seedRates(ctx, null);

    const banner = (ctx.fixture.nativeElement as HTMLElement).querySelector('.rate-gap-banner');
    expect(banner).toBeNull();
  });

  it('el botón del banner navega a planes y pre-carga el rango faltante en Generar calendario', async () => {
    const ctx = setup('overview');
    await seedRates(ctx, {
      rate_last_date: '2026-07-25',
      inventory_last_date: '2026-10-22',
      gap_nights: 89,
      gap_start: '2026-07-26',
      gap_end: '2026-10-22',
    });

    const btn = (ctx.fixture.nativeElement as HTMLElement).querySelector('.rate-gap-banner .rate-gap-btn') as HTMLButtonElement;
    expect(btn).not.toBeNull();
    btn.click();

    expect(ctx.component.generateStartDate()).toBe('2026-07-26');
    expect(ctx.component.generateEndDate()).toBe('2026-10-22');
    expect(ctx.router.navigate).toHaveBeenCalledWith(
      [],
      expect.objectContaining({ queryParamsHandling: 'merge', queryParams: { section: 'plans' } }),
    );
  });

  it('resalta el panel de entrada individual de tarifa en modo insert (rate-entry)', async () => {
    const ctx = setup('rate-entry');
    await seedRates(ctx);

    const panel = panelByHeading(ctx.fixture, 'Entrada individual de tarifa');
    expect(panel).toBeDefined();
    expect(ctx.mode.mode()).toBe('insert');
    expect(panel.classList.contains('mode-active')).toBe(true);
  });

  it('resalta los paneles de form de la sección plans (generar calendario + nuevo plan)', async () => {
    const ctx = setup('plans');
    await seedRates(ctx);

    const generatePanel = panelByHeading(ctx.fixture, 'Generar calendario');
    const planForm = (ctx.fixture.nativeElement as HTMLElement).querySelector('.plan-form-section') as HTMLElement;
    expect(generatePanel).toBeDefined();
    expect(planForm).toBeDefined();
    expect(generatePanel.classList.contains('mode-active')).toBe(true);
    expect(planForm.classList.contains('mode-active')).toBe(true);
  });

  it('resalta el panel de nueva regla de temporada en la sección seasons', async () => {
    const ctx = setup('seasons');
    await seedRates(ctx);

    const panel = panelByHeading(ctx.fixture, 'Nueva regla de temporada');
    expect(panel).toBeDefined();
    expect(ctx.mode.mode()).toBe('insert');
    expect(panel.classList.contains('mode-active')).toBe(true);
  });

  it('al editar una promoción tiñe la caja con el color de update y hace scroll hasta ella', async () => {
    const scrollIntoView = jest.fn();
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
      value: scrollIntoView,
      configurable: true,
      writable: true,
    });

    const ctx = setup();
    await seedRates(ctx);
    const panel = promoPanel(ctx.fixture);

    ctx.component.onEditPromo(promoRow);
    ctx.fixture.detectChanges();

    expect(ctx.mode.mode()).toBe('update');
    expect(ctx.mode.detail()).toBe('Verano');
    expect(panel.classList.contains('mode-active')).toBe(true);
    // El color de update mezcla warning+danger (naranja del mode-indicator).
    expect(panel.style.getPropertyValue('--op-color')).toContain('--danger');
    expect(scrollIntoView).toHaveBeenCalledTimes(1);
  });

  it('no filtra el modo de edición entre secciones al navegar (la edición se cancela al salir)', async () => {
    const ctx = setup('promos');
    await seedRates(ctx);

    ctx.component.onEditPromo(promoRow);
    ctx.fixture.detectChanges();
    expect(ctx.mode.mode()).toBe('update');
    expect(ctx.mode.detail()).toBe('Verano');

    // Navegar a la sección plans → la edición de promos se cancela y el modo
    // vuelve al default de la sección (insert, no EDITANDO heredado).
    ctx.queryParams.next(convertToParamMap({ prop_id: '1', section: 'plans' }));
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();

    expect(ctx.component.editingPromo()).toBeNull();
    expect(ctx.mode.mode()).toBe('insert');
    expect(ctx.mode.detail()).toBe('Plan tarifario');
  });

  it('rechaza crear un plan con tarifa base menor al mínimo ($10 por defecto)', async () => {
    const ctx = setup('plans');
    await seedRates(ctx);
    const createRatePlan = jest.fn();
    (ctx.api as unknown as { createRatePlan: jest.Mock }).createRatePlan = createRatePlan;

    ctx.component.planName.set('Plan barato');
    ctx.component.planBaseRate.set(9.99);
    ctx.component.createRatePlan();
    ctx.fixture.detectChanges();

    expect(createRatePlan).not.toHaveBeenCalled();
    expect(ctx.toast.toasts().some(
      (t) => t.type === 'error' && t.message.includes('mínima') && t.message.includes('10'),
    )).toBe(true);
  });

  it('permite crear un plan con tarifa base igual al mínimo', async () => {
    const ctx = setup('plans');
    await seedRates(ctx);
    const createRatePlan = jest.fn(() => of({}));
    (ctx.api as unknown as { createRatePlan: jest.Mock }).createRatePlan = createRatePlan;

    ctx.component.planName.set('Plan mínimo');
    ctx.component.planBaseRate.set(10);
    ctx.component.createRatePlan();
    ctx.fixture.detectChanges();

    expect(createRatePlan).toHaveBeenCalledWith(expect.objectContaining({ baseRate: 10 }));
    // El reload del recurso tras crear se responde para no dejar requests abiertos.
    ctx.http.expectOne('/api/management/rates?prop_id=1').flush({});
  });

  it('lee el umbral mínimo del envelope y valida con él (min_base_rate configurable)', async () => {
    const ctx = setup('plans');
    await seedRates(ctx, null, [], [], [], 20);
    const createRatePlan = jest.fn(() => of({}));
    (ctx.api as unknown as { createRatePlan: jest.Mock }).createRatePlan = createRatePlan;

    expect(ctx.component.planMinBaseRate()).toBe(20);

    // 15 < 20 → bloqueado sin llamada a la API.
    ctx.component.planName.set('Plan quince');
    ctx.component.planBaseRate.set(15);
    ctx.component.createRatePlan();
    ctx.fixture.detectChanges();
    expect(createRatePlan).not.toHaveBeenCalled();
    expect(ctx.toast.toasts().some((t) => t.type === 'error' && t.message.includes('20'))).toBe(true);

    // 20 == umbral → permitido.
    ctx.component.planBaseRate.set(20);
    ctx.component.createRatePlan();
    ctx.fixture.detectChanges();
    expect(createRatePlan).toHaveBeenCalledWith(expect.objectContaining({ baseRate: 20 }));
    ctx.http.expectOne('/api/management/rates?prop_id=1').flush({});
  });

  it('muestra el botón Cancelar en el form de plan al editar y limpia la edición', async () => {
    const ctx = setup('plans');
    await seedRates(ctx);

    ctx.component.onEditPlan({
      id: 'RP-1',
      name: 'Estándar',
      description: '',
      baseRateLabel: '100 USD',
      baseRate: 100,
      currency: 'USD',
      applicableRoomTypes: [],
      activeLabel: 'Sí',
      includedAmenities: [],
    });
    ctx.fixture.detectChanges();
    expect(ctx.mode.mode()).toBe('update');

    const btn = (ctx.fixture.nativeElement as HTMLElement).querySelector('.plan-form-section .form-actions .btn-secondary') as HTMLButtonElement;
    expect(btn).not.toBeNull();
    expect(btn.textContent).toContain('Cancelar');

    btn.click();
    ctx.fixture.detectChanges();

    expect(ctx.component.editingPlan()).toBeNull();
    expect(ctx.mode.mode()).toBe('insert');
  });

  it('muestra el botón Cancelar en el form de regla de temporada al editar y limpia la edición', async () => {
    const ctx = setup('seasons');
    await seedRates(ctx);

    ctx.component.onEditSeason({
      ruleId: 'SR-1',
      ratePlanId: 'RP-1',
      name: 'Temporada alta',
      startDate: '2026-08-01',
      endDate: '2026-12-31',
      priceOverride: 150,
    });
    ctx.fixture.detectChanges();
    expect(ctx.mode.mode()).toBe('update');

    const panel = panelByHeading(ctx.fixture, 'Nueva regla de temporada');
    const btn = panel.querySelector('.form-actions .btn-secondary') as HTMLButtonElement;
    expect(btn).not.toBeNull();
    expect(btn.textContent).toContain('Cancelar');

    btn.click();
    ctx.fixture.detectChanges();

    expect(ctx.component.editingSeason()).toBeNull();
    expect(ctx.mode.mode()).toBe('insert');
  });

  it('al cancelar la edición con el botón Cancelar, el modo vuelve a insert', async () => {
    const ctx = setup();
    await seedRates(ctx);

    ctx.component.onEditPromo(promoRow);
    ctx.fixture.detectChanges();
    expect(ctx.mode.mode()).toBe('update');
    expect(ctx.mode.detail()).toBe('Verano');

    const cancelBtn = (ctx.fixture.nativeElement as HTMLElement).querySelector('.form-actions .btn-secondary') as HTMLButtonElement;
    cancelBtn.click();
    ctx.fixture.detectChanges();

    // El detalle de la edición se limpia y la sección vuelve al modo de creación.
    expect(ctx.component.editingPromo()).toBeNull();
    expect(ctx.mode.mode()).toBe('insert');
    expect(ctx.mode.detail()).toBe('Promoción');
  });

  const flush = () => new Promise<void>((resolve) => setTimeout(resolve, 0));

  it('el form de Generar calendario no marca los campos como opcionales', async () => {
    const ctx = setup('plans');
    await seedRates(ctx);

    const generatePanel = panelByHeading(ctx.fixture, 'Generar calendario');
    expect(generatePanel).toBeDefined();
    expect(generatePanel.textContent).not.toContain('opcional');
  });

  it('al generar sin fechas muestra error y no llama a la API', async () => {
    const ctx = setup('plans');
    await seedRates(ctx);
    const generateCalendar = jest.fn();
    (ctx.api as unknown as { generateCalendar: jest.Mock }).generateCalendar = generateCalendar;

    ctx.component.generateStartDate.set('');
    ctx.component.generateEndDate.set('');
    void ctx.component.generateCalendar();
    ctx.fixture.detectChanges();

    expect(generateCalendar).not.toHaveBeenCalled();
    expect(ctx.toast.toasts().some((t) => t.type === 'error' && t.message.includes('fechas'))).toBe(true);
  });

  it('al generar con fechas hace dry-run, abre el modal con el conteo y al confirmar escribe', async () => {
    const ctx = setup('plans');
    await seedRates(ctx, null, [{
      rate_plan_id: 'RP-1', name: 'Estándar', base_rate: 100, base_rate_label: '100 USD',
      currency: 'USD', room_type_id: '', is_active: true,
    }]);
    const api = ctx.api as unknown as { generateCalendar: jest.Mock };
    api.generateCalendar = jest.fn(() => of({ entries_generated: 5, start_date: '2026-08-09', end_date: '2026-09-06' }));
    const confirmDialog = TestBed.inject(ConfirmDialogService);

    ctx.component.generateRatePlanId.set('RP-1');
    ctx.component.generateStartDate.set('2026-08-09');
    ctx.component.generateEndDate.set('2026-09-06');
    void ctx.component.generateCalendar();
    await flush();
    ctx.fixture.detectChanges();

    // 1) Primero dry-run (cuenta sin escribir) con el rango y el plan.
    expect(api.generateCalendar).toHaveBeenCalledWith(expect.objectContaining({
      dryRun: true, ratePlanId: 'RP-1', startDate: '2026-08-09', endDate: '2026-09-06',
    }));
    // 2) Modal abierto con el conteo exacto, el plan y el rango.
    expect(confirmDialog.isOpen()).toBe(true);
    expect(confirmDialog.config().message).toContain('5');
    expect(confirmDialog.config().details?.join(' ')).toContain('Estándar');
    expect(confirmDialog.config().details?.join(' ')).toContain('2026-08-09 → 2026-09-06');

    // 3) Confirmar → genera de verdad (sin dry-run) y avisa por toast.
    confirmDialog.confirm();
    await flush();
    ctx.fixture.detectChanges();

    expect(api.generateCalendar).toHaveBeenLastCalledWith(expect.objectContaining({ dryRun: false }));
    expect(ctx.toast.toasts().some((t) => t.message.includes('Calendario generado'))).toBe(true);
    // El reload del recurso tras generar se responde para no dejar requests abiertos.
    ctx.http.expectOne('/api/management/rates?prop_id=1').flush({});
  });

  it('muestra el modo EXECUTE en el mode-indicator mientras el modal está abierto y lo restaura al cerrar', async () => {
    const ctx = setup('plans');
    await seedRates(ctx);
    const api = ctx.api as unknown as { generateCalendar: jest.Mock };
    api.generateCalendar = jest.fn(() => of({ entries_generated: 5, start_date: '2026-08-09', end_date: '2026-09-06' }));
    const confirmDialog = TestBed.inject(ConfirmDialogService);

    // Base de la sección plans: insert · Plan tarifario.
    expect(ctx.mode.mode()).toBe('insert');

    ctx.component.generateStartDate.set('2026-08-09');
    ctx.component.generateEndDate.set('2026-09-06');
    void ctx.component.generateCalendar();
    await flush();
    ctx.fixture.detectChanges();

    // Mientras el modal está abierto → EXECUTE (como monitoring).
    expect(confirmDialog.isOpen()).toBe(true);
    expect(ctx.mode.mode()).toBe('execute');
    expect(ctx.mode.detail()).toBe('Generar calendario');

    // Al cancelar, el modo vuelve al default de la sección (insert · Plan tarifario),
    // no queda en 'Solo lectura' por la liberación del transient del modal.
    confirmDialog.cancel();
    await flush();
    ctx.fixture.detectChanges();
    expect(confirmDialog.isOpen()).toBe(false);
    expect(ctx.mode.mode()).toBe('insert');
    expect(ctx.mode.detail()).toBe('Plan tarifario');
  });

  it('al actualizar lote sin datos completos muestra toast de error y no llama a la API', async () => {
    const ctx = setup('calendar');
    await seedRates(ctx);
    const batchUpdateCalendar = jest.fn();
    (ctx.api as unknown as { batchUpdateCalendar: jest.Mock }).batchUpdateCalendar = batchUpdateCalendar;

    ctx.component.batchRatePlanId.set('');
    ctx.component.batchStartDate.set('');
    ctx.component.batchEndDate.set('');
    ctx.component.batchRateAmount.set(0);
    ctx.component.batchUpdateCalendar();
    ctx.fixture.detectChanges();

    expect(batchUpdateCalendar).not.toHaveBeenCalled();
    expect(ctx.toast.toasts().some((t) => t.type === 'error')).toBe(true);
  });

  it('al actualizar lote hace dry-run, abre el modal con el conteo y al confirmar aplica', async () => {
    const ctx = setup('calendar');
    await seedRates(ctx, null, [{
      rate_plan_id: 'RP-1', name: 'Estándar', base_rate: 100, base_rate_label: '100 USD',
      currency: 'USD', room_type_id: '', is_active: true,
    }]);
    const api = ctx.api as unknown as { batchUpdateCalendar: jest.Mock };
    api.batchUpdateCalendar = jest.fn(() => of({ affected_days: 5, start_date: '2026-08-09', end_date: '2026-08-13', rate_plan_id: 'RP-1' }));
    const confirmDialog = TestBed.inject(ConfirmDialogService);

    ctx.component.batchRatePlanId.set('RP-1');
    ctx.component.batchStartDate.set('2026-08-09');
    ctx.component.batchEndDate.set('2026-08-13');
    ctx.component.batchRateAmount.set(120);
    ctx.component.batchUpdateCalendar();
    await flush();
    ctx.fixture.detectChanges();

    // 1) Primero dry-run con el rango, el plan y la tarifa.
    expect(api.batchUpdateCalendar).toHaveBeenCalledWith(expect.objectContaining({
      dryRun: true, ratePlanId: 'RP-1', startDate: '2026-08-09', endDate: '2026-08-13', rateAmount: 120,
    }));
    // 2) Modal abierto con el conteo exacto, el plan y el rango.
    expect(confirmDialog.isOpen()).toBe(true);
    expect(confirmDialog.config().message).toContain('5');
    expect(confirmDialog.config().details?.join(' ')).toContain('Estándar');
    expect(confirmDialog.config().details?.join(' ')).toContain('2026-08-09 → 2026-08-13');

    // 3) Confirmar → aplica de verdad (sin dry-run) y avisa por toast.
    confirmDialog.confirm();
    await flush();
    ctx.fixture.detectChanges();

    expect(api.batchUpdateCalendar).toHaveBeenLastCalledWith(expect.objectContaining({ dryRun: false }));
    expect(ctx.toast.toasts().some((t) => t.message.includes('Calendario actualizado por lote'))).toBe(true);
    // El reload del recurso tras aplicar se responde para no dejar requests abiertos.
    ctx.http.expectOne('/api/management/rates?prop_id=1').flush({});
  });

  it('al cancelar el modal de lote no aplica cambios', async () => {
    const ctx = setup('calendar');
    await seedRates(ctx);
    const api = ctx.api as unknown as { batchUpdateCalendar: jest.Mock };
    api.batchUpdateCalendar = jest.fn(() => of({ affected_days: 5, start_date: '2026-08-09', end_date: '2026-08-13', rate_plan_id: 'RP-1' }));
    const confirmDialog = TestBed.inject(ConfirmDialogService);

    ctx.component.batchRatePlanId.set('RP-1');
    ctx.component.batchStartDate.set('2026-08-09');
    ctx.component.batchEndDate.set('2026-08-13');
    ctx.component.batchRateAmount.set(120);
    ctx.component.batchUpdateCalendar();
    await flush();
    ctx.fixture.detectChanges();
    expect(confirmDialog.isOpen()).toBe(true);

    confirmDialog.cancel();
    await flush();
    ctx.fixture.detectChanges();

    expect(api.batchUpdateCalendar).toHaveBeenCalledTimes(1); // solo el dry-run
    expect(confirmDialog.isOpen()).toBe(false);
  });

  it('propaga source=generated del calendario hasta las celdas del calendario mensual', async () => {
    const ctx = setup('calendar');
    await seedRates(
      ctx,
      null,
      [{
        rate_plan_id: 'RP-1', name: 'Estándar', base_rate: 100, base_rate_label: '100 USD',
        currency: 'USD', room_type_id: 'RT-1-STD', is_active: true,
      }],
      [{
        date: '2026-08-10', rate_plan_id: 'RP-1', plan_name: 'Estándar', rate_amount: 120,
        rate_amount_label: '120 USD', min_stay_nights: 1, is_closed: false, source: 'generated',
      }],
      [{ room_type_id: 'RT-1-STD', name: 'Estándar' }],
    );
    ctx.component.calendarMonth.set(7);
    ctx.component.calendarYear.set(2026);
    ctx.component.calendarDisplayMode.set('month');
    ctx.fixture.detectChanges();

    const rows = ctx.component.calendarRows();
    expect(rows.length).toBe(1);
    expect(rows[0].days[0].source).toBe('generated');
  });

  it('muestra el modo EXECUTE mientras el modal de lote está abierto y lo restaura al cerrar', async () => {
    const ctx = setup('calendar');
    await seedRates(ctx);
    const api = ctx.api as unknown as { batchUpdateCalendar: jest.Mock };
    api.batchUpdateCalendar = jest.fn(() => of({ affected_days: 5, start_date: '2026-08-09', end_date: '2026-08-13', rate_plan_id: 'RP-1' }));
    const confirmDialog = TestBed.inject(ConfirmDialogService);

    // Base de la sección calendar: Solo lectura.
    expect(ctx.mode.mode()).toBe('read');

    ctx.component.batchRatePlanId.set('RP-1');
    ctx.component.batchStartDate.set('2026-08-09');
    ctx.component.batchEndDate.set('2026-08-13');
    ctx.component.batchRateAmount.set(120);
    ctx.component.batchUpdateCalendar();
    await flush();
    ctx.fixture.detectChanges();

    expect(confirmDialog.isOpen()).toBe(true);
    expect(ctx.mode.mode()).toBe('execute');
    expect(ctx.mode.detail()).toBe('Actualizar lote');

    confirmDialog.cancel();
    await flush();
    ctx.fixture.detectChanges();
    expect(confirmDialog.isOpen()).toBe(false);
    expect(ctx.mode.mode()).toBe('read');
  });

  it('al cancelar el modal no genera entradas', async () => {
    const ctx = setup('plans');
    await seedRates(ctx);
    const api = ctx.api as unknown as { generateCalendar: jest.Mock };
    api.generateCalendar = jest.fn(() => of({ entries_generated: 5, start_date: '2026-08-09', end_date: '2026-09-06' }));
    const confirmDialog = TestBed.inject(ConfirmDialogService);

    ctx.component.generateStartDate.set('2026-08-09');
    ctx.component.generateEndDate.set('2026-09-06');
    void ctx.component.generateCalendar();
    await flush();
    ctx.fixture.detectChanges();
    expect(confirmDialog.isOpen()).toBe(true);

    confirmDialog.cancel();
    await flush();
    ctx.fixture.detectChanges();

    // Solo se hizo el dry-run; nunca la generación real.
    expect(api.generateCalendar).toHaveBeenCalledTimes(1);
    expect(confirmDialog.isOpen()).toBe(false);
  });
});
