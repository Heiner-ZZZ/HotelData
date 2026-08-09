import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { BehaviorSubject, of, Subject } from 'rxjs';

import { OperationModeService } from '../../../../core/services/operation-mode.service';
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
    };
  }

  /** Resolve the rates httpResource so viewState reaches 'success' (promos panel renders). */
  async function seedRates(ctx: { http: HttpTestingController; fixture: { detectChanges(): void } }) {
    ctx.http.expectOne('/api/management/rates?prop_id=1').flush({
      prop_id: 1,
      hotel_label: 'Hotel Test',
      room_types: [],
      rate_plans: [],
      calendar: [],
      rate_rules: [],
      promotions: [],
      coupon_codes: [],
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
});
