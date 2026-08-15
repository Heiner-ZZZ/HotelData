import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { httpErrorInterceptor } from '../../../../core/api/http-error.interceptor';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import type { RatesViewModel } from '../../models/rates.model';
import type { PromoEditState } from './promotion-form';
import { PromotionFormComponent } from './promotion-form';

describe('PromotionFormComponent', () => {
  /** Campaña con cupones usados → ninguna edición se puede guardar. */
  const promo: PromoEditState = {
    campaignId: 'PC-1-verano',
    name: 'Verano',
    description: 'Verano 2026',
    discountPercent: 15,
    couponCount: 10,
    couponUsed: 3,
    startDate: '2026-08-01',
    endDate: '2026-12-31',
    isActive: true,
  };

  /** Campaña sin cupones usados → la edición normal sí es posible. */
  const cleanPromo: PromoEditState = { ...promo, couponUsed: 0 };

  const viewModel: RatesViewModel = {
    propId: 1,
    hotelLabel: 'Hotel Test',
    manualOverride: false,
    profileBadge: 'Nombre generado',
    roomTypes: [],
    ratePlans: [],
    calendar: [],
    rateRules: [],
    seasonalRules: [],
    promotions: [],
    coupons: [],
  };

  function setup() {
    const confirmDialog = { open: jest.fn(() => Promise.resolve(true)) };
    TestBed.configureTestingModule({
      imports: [PromotionFormComponent],
      providers: [
        // El interceptor real convierte el detail de FastAPI en ApiError.message
        // (el error del backend que se muestra inline).
        provideHttpClient(withInterceptors([httpErrorInterceptor])),
        provideHttpClientTesting(),
        { provide: ConfirmDialogService, useValue: confirmDialog },
      ],
    });
    const fixture = TestBed.createComponent(PromotionFormComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    const http = TestBed.inject(HttpTestingController);
    return { fixture, component, http, confirmDialog };
  }

  /** Flush the forkJoin refresh (3 GETs) that runs after a successful save. */
  function flushRefresh(http: HttpTestingController) {
    http.expectOne((req) => req.method === 'GET' && req.urlWithParams.includes('/management/rates?prop_id=1'))
      .flush({ prop_id: 1, hotel_label: 'Hotel Test', rate_plans: [], calendar: [], rate_rules: [], promotions: [], coupon_codes: [] });
    http.expectOne((req) => req.method === 'GET' && req.urlWithParams.includes('/management/rates/options'))
      .flush({ properties: [], rate_plans: [] });
    http.expectOne((req) => req.method === 'GET' && req.urlWithParams.includes('/management/promotions'))
      .flush({ campaigns: [], total: 0 });
  }

  function editPromo(
    ctx: { fixture: { componentRef: { setInput(name: string, value: unknown): void }; detectChanges(): void }; component: PromotionFormComponent },
    toEdit: PromoEditState = cleanPromo,
  ) {
    ctx.fixture.componentRef.setInput('editingPromo', toEdit);
    ctx.fixture.detectChanges();
  }

  it('shows no reduction warning when creating', () => {
    const { component } = setup();
    expect(component.couponsToRetire()).toBeNull();
  });

  it('shows no warning when the coupon count is kept equal on edit', () => {
    const ctx = setup();
    editPromo(ctx);
    expect(ctx.component.couponsToRetire()).toBeNull();
  });

  it('reports how many unused coupons will be retired when the count is reduced', () => {
    const ctx = setup();
    editPromo(ctx);

    ctx.component.form.controls.couponCount.setValue(4);
    expect(ctx.component.couponsToRetire()).toBe(6); // 10 → 4 retira 6

    ctx.component.form.controls.couponCount.setValue(1);
    expect(ctx.component.couponsToRetire()).toBe(9);
  });

  it('clears the warning when the count returns to the original value', () => {
    const ctx = setup();
    editPromo(ctx);

    ctx.component.form.controls.couponCount.setValue(3);
    expect(ctx.component.couponsToRetire()).toBe(7);

    ctx.component.form.controls.couponCount.setValue(10);
    expect(ctx.component.couponsToRetire()).toBeNull();
  });

  it('shows no warning when the count is increased', () => {
    const ctx = setup();
    editPromo(ctx);

    ctx.component.form.controls.couponCount.setValue(15);
    expect(ctx.component.couponsToRetire()).toBeNull();
  });

  it('renders the reduction warning in the DOM when the count is reduced', () => {
    const ctx = setup();
    editPromo(ctx);

    ctx.component.form.controls.couponCount.setValue(4);
    ctx.fixture.detectChanges();

    const text = (ctx.fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Se retirarán 6 cupones sin usar.');
  });

  it('clears the warning after cancelling the edit', async () => {
    const ctx = setup();
    editPromo(ctx);

    ctx.component.form.controls.couponCount.setValue(5);
    expect(ctx.component.couponsToRetire()).toBe(5);

    await ctx.component.cancelEdit();
    expect(ctx.component.couponsToRetire()).toBeNull();
  });

  it('renders an explicit Cancelar button only while editing', () => {
    const ctx = setup();
    ctx.fixture.detectChanges();
    const actions = (ctx.fixture.nativeElement as HTMLElement).querySelector('.form-actions');
    expect(actions?.textContent ?? '').not.toContain('Cancelar');

    editPromo(ctx);
    ctx.fixture.detectChanges();
    const btn = (ctx.fixture.nativeElement as HTMLElement).querySelector('.form-actions .btn-secondary');
    expect(btn).not.toBeNull();
    expect(btn?.textContent).toContain('Cancelar');
  });

  it('clears the edit and notifies the page when the cancel button is clicked', async () => {
    const ctx = setup();
    editPromo(ctx);

    ctx.component.form.controls.couponCount.setValue(5);
    expect(ctx.component.couponsToRetire()).toBe(5);

    const cancelled: number[] = [];
    ctx.component.cancelEditChange.subscribe(() => cancelled.push(1));

    const btn = (ctx.fixture.nativeElement as HTMLElement).querySelector('.form-actions .btn-secondary') as HTMLButtonElement;
    btn.click();
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();

    expect(cancelled).toEqual([1]);
    expect(ctx.component.isEditing()).toBe(false);
    expect(ctx.component.couponsToRetire()).toBeNull();
    // El form vuelve a los defaults de creación (la página queda lista para crear).
    expect(ctx.component.form.getRawValue().couponCount).toBe(10);
  });

  it('pregunta antes de cancelar cuando hay cambios sin guardar y descarta al confirmar', async () => {
    const ctx = setup();
    editPromo(ctx);

    ctx.component.form.controls.couponCount.setValue(5);
    await ctx.component.cancelEdit();

    expect(ctx.confirmDialog.open).toHaveBeenCalledTimes(1);
    expect(ctx.confirmDialog.open).toHaveBeenCalledWith(expect.objectContaining({
      title: 'Descartar cambios',
    }));
    expect(ctx.component.isEditing()).toBe(false);
  });

  it('mantiene la edición si se cancela la confirmación', async () => {
    const ctx = setup();
    editPromo(ctx);

    ctx.component.form.controls.couponCount.setValue(5);
    const cancelled: number[] = [];
    ctx.component.cancelEditChange.subscribe(() => cancelled.push(1));

    (ctx.confirmDialog.open as jest.Mock).mockResolvedValueOnce(false);
    await ctx.component.cancelEdit();

    expect(ctx.component.isEditing()).toBe(true);
    expect(ctx.component.form.controls.couponCount.value).toBe(5);
    expect(cancelled).toEqual([]);
  });

  it('no pregunta si no hay cambios sin guardar', async () => {
    const ctx = setup();
    editPromo(ctx);

    await ctx.component.cancelEdit();

    expect(ctx.confirmDialog.open).not.toHaveBeenCalled();
    expect(ctx.component.isEditing()).toBe(false);
  });

  it('muestra el indicador de cambios sin guardar en el botón Guardar al editar con modificaciones', () => {
    const ctx = setup();
    editPromo(ctx);

    ctx.component.form.controls.couponCount.setValue(4);
    ctx.fixture.detectChanges();

    const dot = (ctx.fixture.nativeElement as HTMLElement).querySelector('.form-actions .unsaved-dot');
    expect(dot).not.toBeNull();
  });

  it('no muestra el indicador de cambios sin guardar sin modificaciones', () => {
    const ctx = setup();
    editPromo(ctx);
    ctx.fixture.detectChanges();

    const dot = (ctx.fixture.nativeElement as HTMLElement).querySelector('.form-actions .unsaved-dot');
    expect(dot).toBeNull();
  });

  it('no muestra el indicador de cambios sin guardar en modo crear', () => {
    const ctx = setup();
    ctx.fixture.detectChanges();

    const dot = (ctx.fixture.nativeElement as HTMLElement).querySelector('.form-actions .unsaved-dot');
    expect(dot).toBeNull();
  });

  it('reports how many coupons were retired in the toast when a reduction is saved', () => {
    const { fixture, component, http } = setup();
    fixture.componentRef.setInput('viewModel', viewModel);
    editPromo({ fixture, component });

    component.form.controls.couponCount.setValue(4);
    const messages: string[] = [];
    component.messageChange.subscribe((m) => messages.push(m));

    component.submit();
    http.expectOne((req) => req.method === 'PUT' && req.url.includes('/management/promotions/PC-1-verano'))
      .flush({ campaign_id: 'PC-1-verano', coupons_retired: 6 });
    flushRefresh(http);

    expect(messages).toEqual(['Promoción actualizada · 6 cupones retirados']);
  });

  it('keeps the plain update toast when the count is unchanged (no retired)', () => {
    const { fixture, component, http } = setup();
    fixture.componentRef.setInput('viewModel', viewModel);
    editPromo({ fixture, component });

    const messages: string[] = [];
    component.messageChange.subscribe((m) => messages.push(m));

    component.submit();
    http.expectOne((req) => req.method === 'PUT' && req.url.includes('/management/promotions/PC-1-verano'))
      .flush({ campaign_id: 'PC-1-verano', coupons_retired: 0 });
    flushRefresh(http);

    expect(messages).toEqual(['Promoción actualizada']);
  });

  it('keeps the plain create toast (no retired count)', () => {
    const { fixture, component, http } = setup();
    fixture.componentRef.setInput('viewModel', viewModel);

    component.form.patchValue({ name: 'Verano', startDate: '2026-08-01', endDate: '2026-12-31' });
    const messages: string[] = [];
    component.messageChange.subscribe((m) => messages.push(m));

    component.submit();
    http.expectOne((req) => req.method === 'POST' && req.url.includes('/management/promotions'))
      .flush({ campaign_id: 'PC-1-verano' });
    flushRefresh(http);

    expect(messages).toEqual(['Promoción creada']);
  });

  it('blocks the save and shows the proactive notice when the campaign has used coupons', () => {
    const { fixture, component, http } = setup();
    fixture.componentRef.setInput('viewModel', viewModel);
    editPromo({ fixture, component }, promo); // couponUsed: 3

    expect(component.usedCouponsBlock()).toBe(3);

    component.submit();
    // NINGÚN request sale: el guardado está bloqueado client-side, sin esperar
    // el error del backend.
    http.expectNone((req) => req.method === 'PUT' || req.method === 'POST');
    http.verify();

    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('3 cupones usados');
    expect(text).toContain('desactiva y crea una nueva');
  });

  it('uses the singular form for a single used coupon', () => {
    const { fixture, component } = setup();
    fixture.componentRef.setInput('viewModel', viewModel);
    editPromo({ fixture, component }, { ...promo, couponUsed: 1 });

    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('1 cupón usado');
  });

  it('shows no used-coupons notice when the campaign has no used coupons', () => {
    const { fixture, component } = setup();
    fixture.componentRef.setInput('viewModel', viewModel);
    editPromo({ fixture, component }, cleanPromo);

    expect(component.usedCouponsBlock()).toBeNull();
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).not.toContain('cupones usados');
  });

  it('shows no used-coupons notice when creating', () => {
    const { fixture, component } = setup();

    expect(component.usedCouponsBlock()).toBeNull();
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).not.toContain('cupones usados');
  });

  it('shows other backend errors inline when the save is rejected', () => {
    // Una campaña SIN cupones usados sí llega al backend — si este rechaza
    // (p.ej. campaña vencida), el error se muestra inline en el form.
    const { fixture, component, http } = setup();
    fixture.componentRef.setInput('viewModel', viewModel);
    editPromo({ fixture, component }, cleanPromo);

    component.submit();
    http.expectOne((req) => req.method === 'PUT' && req.url.includes('/management/promotions/PC-1-verano'))
      .flush(
        { detail: 'No se puede editar una campaña que ya ha vencido.' },
        { status: 400, statusText: 'Bad Request' }
      );

    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('No se puede editar una campaña que ya ha vencido.');
  });

  // ── Conflicto de código estructurado (COUPON_CODE_EXISTS) ──

  const CONFLICT_BODY = {
    detail: {
      message: 'El código LUNA15 ya existe en la campaña «Luna de miel» de Tarifas. Vincúlala en lugar de crear una nueva.',
      code: 'COUPON_CODE_EXISTS',
      campaign_id: 'PC-1-luna-de-miel',
      campaign_name: 'Luna de miel',
      coupon_code: 'LUNA15',
    },
  };

  /** Llena el form en modo crear con el cupón conflictivo y dispara submit. */
  function submitConflict(ctx: {
    component: PromotionFormComponent;
    http: HttpTestingController;
  }): void {
    ctx.component.form.patchValue({
      name: 'Verano',
      startDate: '2026-08-01',
      endDate: '2026-12-31',
      couponCode: 'LUNA15',
    });
    ctx.component.submit();
    ctx.http
      .expectOne((req) => req.method === 'POST' && req.url.includes('/management/promotions'))
      .flush(CONFLICT_BODY, { status: 400, statusText: 'Bad Request' });
  }

  it('muestra el conflicto de código como banner destacado al crear (campaña dueña + código)', () => {
    const { fixture, component, http } = setup();
    fixture.componentRef.setInput('viewModel', viewModel);
    const errors: string[] = [];
    component.errorChange.subscribe((m) => errors.push(m));

    submitConflict({ component, http });
    fixture.detectChanges();

    const el = fixture.nativeElement as HTMLElement;
    const banner = el.querySelector('.coupon-conflict-banner');
    expect(banner).not.toBeNull();
    expect(banner?.textContent).toContain('LUNA15');
    expect(banner?.textContent).toContain('Luna de miel');
    expect(component.couponConflict()).not.toBeNull();
    expect(component.couponConflict()?.campaign_id).toBe('PC-1-luna-de-miel');
    // El banner reemplaza el inline genérico y NO dispara el toast del padre
    // (el interceptor global ya avisa) — sin doble notificación.
    expect(component.inlineError()).toBeNull();
    expect(errors).toEqual([]);
  });

  it('limpia el banner de conflicto al cambiar el código de cupón', () => {
    const { fixture, component, http } = setup();
    fixture.componentRef.setInput('viewModel', viewModel);

    submitConflict({ component, http });
    fixture.detectChanges();
    expect(component.couponConflict()).not.toBeNull();

    component.form.controls.couponCode.setValue('OTRO20');
    fixture.detectChanges();

    expect(component.couponConflict()).toBeNull();
    expect(
      (fixture.nativeElement as HTMLElement).querySelector('.coupon-conflict-banner'),
    ).toBeNull();
  });

  it('permite quitar el código conflictivo desde el banner', () => {
    const { fixture, component, http } = setup();
    fixture.componentRef.setInput('viewModel', viewModel);

    submitConflict({ component, http });
    fixture.detectChanges();
    const el = fixture.nativeElement as HTMLElement;
    const clearBtn = el.querySelector('.coupon-conflict-clear');
    expect(clearBtn).not.toBeNull();

    (clearBtn as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(component.form.controls.couponCode.value).toBe('');
    expect(component.couponConflict()).toBeNull();
    expect(el.querySelector('.coupon-conflict-banner')).toBeNull();
  });
});
