import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import type { PromoEditState } from '../../components/promotion-form/promotion-form';
import { httpResource } from '@angular/common/http';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, forkJoin, map, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import type { RatePlanOption, RatesViewModel } from '../../models/rates.model';
import type { RatesDto } from '../../models/rates.dto';
import { RatesApiService } from '../../services/rates-api.service';
import { mapRatesResponse } from '../../mappers/rates.mapper';
import { RatePlanTableComponent } from '../../components/rate-plan-table/rate-plan-table';
import { RateCalendarTableComponent } from '../../components/rate-calendar-table/rate-calendar-table';
import { RateSidebarComponent, type SidebarSection } from '../../components/rate-sidebar/rate-sidebar';
import { RateKpiGridComponent, type KpiData } from '../../components/rate-kpi-grid/rate-kpi-grid';
import { RateMonthlyCalendarComponent, type RoomTypeCalendarRow } from '../../components/rate-monthly-calendar/rate-monthly-calendar';
import { PromotionFormComponent } from '../../components/promotion-form/promotion-form';
import { PromotionsTableComponent, type CampaignRow, type CouponRow } from '../../components/promotions-table/promotions-table';
import { SeasonalRulesTableComponent, type SeasonalRuleRow } from '../../components/seasonal-rules-table/seasonal-rules-table';
import { AiSuggestDirective } from '../../../../core/directives/ai-suggest.directive';

@Component({
  selector: 'app-rates-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    PropertySelectorComponent,
    RateSidebarComponent,
    RateKpiGridComponent,
    RateMonthlyCalendarComponent,
    PromotionFormComponent,
    PromotionsTableComponent,
    SeasonalRulesTableComponent,
    RatePlanTableComponent,
    RateCalendarTableComponent,
    AiSuggestDirective,
  ],
  templateUrl: './rates-page.html',
  styleUrl: './rates-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RatesPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(RatesApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly propertyCtx = inject(PropertyContextService);

  /** Prop ID from route — source of truth for current property. */
  private readonly routePropId = toSignal(
    this.route.queryParamMap.pipe(
      map((params) => Number(params.get('prop_id') ?? '0')),
      distinctUntilChanged(),
    ),
    { initialValue: 0 }
  );

  /** Section from URL — declarative, no manual subscription needed. */
  private readonly routeSection = toSignal(
    this.route.queryParamMap.pipe(
      map((params) => params.get('section') || 'overview'),
      distinctUntilChanged(),
    ),
    { initialValue: 'overview' }
  );

  /** Declarative data fetching — auto-fetches when routePropId changes. */
  private readonly ratesResource = httpResource<RatesDto>(() => {
    const propId = this.routePropId();
    return propId > 0 ? `/api/management/rates?prop_id=${propId}` : undefined;
  });

  /* ── State ── */
  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<RatesViewModel | null>(null);
  /** Derived from viewModel — no separate API call needed. */
  readonly ratePlanOptions = computed<RatePlanOption[]>(() =>
    (this.viewModel()?.ratePlans ?? []).map((p) => ({ id: p.id, label: p.name }))
  );
  readonly message = signal('');
  readonly errorMessage = signal('');

  /** Current property ID — derived from URL (source of truth). */
  readonly selectedPropId = computed(() => this.routePropId());

  /** Current property name — derived from loaded data. */
  readonly selectedLabel = computed(() => this.viewModel()?.hotelLabel ?? '');

  /** Current section — derived from URL query param. */
  readonly activeSection = computed(() => this.routeSection());
  readonly editingPlan = signal<{ id: string; name: string; description: string; baseRate: number; currency: string; roomTypeId: string; isActive: boolean } | null>(null);
  readonly deleteConfirm = signal<string | null>(null);
  readonly promoDeleteConfirm = signal<string | null>(null);
  readonly promotionsData = signal<{ campaigns: Array<any>; total: number } | null>(null);
  readonly editingPromo = signal<PromoEditState | null>(null);

  /* ── Form signals (replacing FormBuilder) ── */

  // Plan form
  readonly planName = signal('');
  readonly planDescription = signal('');
  readonly planRoomTypeId = signal('');
  readonly planBaseRate = signal(0);
  readonly planCurrency = signal('USD');
  readonly planIsActive = signal(true);

  // Calendar form
  readonly calendarRatePlanId = signal('');
  readonly calendarDate = signal('');
  readonly calendarRateAmount = signal(0);
  readonly calendarMinStayNights = signal(1);
  readonly calendarIsClosed = signal(false);

  // Batch update form
  readonly batchRatePlanId = signal('');
  readonly batchStartDate = signal('');
  readonly batchEndDate = signal('');
  readonly batchRateAmount = signal(0);
  readonly batchMinStayNights = signal(1);
  readonly batchOnlyWeekends = signal(false);

  // Generate calendar form
  readonly generateRatePlanId = signal('');
  readonly generateStartDate = signal('');
  readonly generateEndDate = signal('');

  // Seasonal rule form
  readonly seasonalRatePlanId = signal('');
  readonly seasonalName = signal('');
  readonly seasonalStartDate = signal('');
  readonly seasonalEndDate = signal('');
  readonly seasonalPriceOverride = signal(0);

  /* ── Sidebar sections ── */
  readonly sidebarSections: SidebarSection[] = [
    { id: 'overview', label: 'Panel', icon: 'dashboard' },
    { id: 'calendar', label: 'Calendario Global', icon: 'calendar_month' },
    { id: 'plans', label: 'Planes Tarifarios', icon: 'table' },
    { id: 'seasons', label: 'Temporadas', icon: 'event' },
    { id: 'promos', label: 'Promociones', icon: 'campaign' },
  ];

  /* ── KPI data derived from viewModel ── */
  readonly kpiData = computed((): KpiData | null => {
    const vm = this.viewModel();
    if (!vm) return null;
    return {
      hotelLabel: vm.hotelLabel,
      profileBadge: vm.profileBadge,
      ratePlansCount: vm.ratePlans.length,
      calendarCount: vm.calendar.length,
      promotionsCount: vm.promotions.length,
      couponsCount: vm.coupons.length,
    };
  });

  /* ── Calendar data derived from viewModel ── */
  readonly calendarMonth = signal(new Date().getMonth());
  readonly calendarYear = signal(new Date().getFullYear());

  readonly calendarRows = computed((): RoomTypeCalendarRow[] => {
    const vm = this.viewModel();
    if (!vm) return [];
    const month = this.calendarMonth();
    const year = this.calendarYear();
    const monthStr = `${year}-${String(month + 1).padStart(2, '0')}`;

    // Rate plan → room type mapping
    const planToRoomType = new Map<string, string>();
    for (const plan of vm.ratePlans) {
      if (plan.roomTypeId) {
        planToRoomType.set(plan.id, plan.roomTypeId);
      }
    }

    return vm.roomTypes.map((rt) => ({
      roomTypeId: rt.id,
      roomTypeName: rt.name,
      days: vm.calendar
        .filter((c) => planToRoomType.get(c.ratePlanId) === rt.id && c.date.startsWith(monthStr))
        .map((c) => {
          const amount = c.rateAmount;
          let tier: 'low' | 'medium' | 'high' | 'premium' = 'medium';
          if (amount < 80) tier = 'low';
          else if (amount < 150) tier = 'medium';
          else if (amount < 250) tier = 'high';
          else tier = 'premium';
          return {
            date: c.date,
            rateAmount: c.rateAmount,
            ratePlanName: c.planName || '-',
            ratePlanId: c.ratePlanId,
            isClosed: c.isClosed,
            minStay: c.minStayNights,
            tier,
          };
        }),
    }));
  });

  /* ── Derived data for tables ── */
  readonly seasonalRuleRows = computed((): SeasonalRuleRow[] => {
    return (this.viewModel()?.seasonalRules ?? []).map((r) => ({
      ruleId: r.ruleId,
      name: r.name,
      ratePlanId: r.ratePlanId,
      rangeLabel: r.rangeLabel,
      priceOverride: r.priceOverride,
    }));
  });

  readonly campaignRows = computed((): CampaignRow[] => {
    const data = this.promotionsData();
    if (data) {
      return data.campaigns.map((p: any) => ({
        campaignId: p.campaign_id,
        name: p.name,
        description: p.description || '',
        discountPercent: p.discount_percent ?? 0,
        isActive: p.is_active,
        startDate: p.start_date || '',
        endDate: p.end_date || '',
        couponTotal: p.coupon_total ?? 0,
        couponUsed: p.coupon_used ?? 0,
        couponAvailable: p.coupon_available ?? 0,
      }));
    }
    return (this.viewModel()?.promotions ?? []).map((p) => ({
      campaignId: p.campaignId,
      name: p.name,
      description: p.description,
      discountPercent: p.discountPercent,
      isActive: p.activeLabel === 'Sí',
      startDate: p.dateRange.split(' → ')[0] || '',
      endDate: p.dateRange.split(' → ')[1] || '',
      couponTotal: 0,
      couponUsed: 0,
      couponAvailable: 0,
    }));
  });

  readonly couponRows = computed((): CouponRow[] => {
    return (this.viewModel()?.coupons ?? []).map((c) => ({
      code: c.code,
      activeLabel: c.activeLabel,
    }));
  });


  get roomTypes() { return this.viewModel()?.roomTypes ?? []; }

  constructor() {
    // ── Sync httpResource → viewModel + viewState ──
    effect(() => {
      const propId = this.selectedPropId();

      if (!propId) {
        this.viewState.set('empty');
        this.viewModel.set(null);
        this.message.set('');
        this.errorMessage.set('');
        this.editingPlan.set(null);
        this.editingPromo.set(null);
        this.deleteConfirm.set(null);
        this.propertyCtx.clear();
        return;
      }

      if (this.ratesResource.isLoading()) {
        this.viewState.set(this.viewModel() ? 'success' : 'loading');
        return;
      }

      if (this.ratesResource.error()) {
        this.viewState.set('error');
        this.errorMessage.set('No se pudo cargar la información.');
        return;
      }

      const dto = this.ratesResource.value();
      if (dto) {
        const data = mapRatesResponse(dto);
        this.viewModel.set(data);
        this.viewState.set('success');
        this.message.set('');
        this.errorMessage.set('');
        this.propertyCtx.setProperty(data.propId, data.hotelLabel);
      }
    }, { allowSignalWrites: true });
  }

  onPropSelected(propId: number): void {
    if (!propId) this.propertyCtx.clear();
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: propId || null },
    });
  }

  onSectionChange(section: string): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParamsHandling: 'merge',
      queryParams: { section },
    });
  }

  onMonthChange(month: number, year: number): void {
    this.calendarMonth.set(month);
    this.calendarYear.set(year);
  }

  /* ── Rate Plan CRUD ── */
  createRatePlan(): void {
    const current = this.viewModel();
    if (!current || !this.planName() || this.planBaseRate() <= 0) { return; }
    const obs = this.editingPlan()
      ? this.api.updateRatePlan(this.editingPlan()!.id, {
          name: this.planName(), description: this.planDescription(), baseRate: this.planBaseRate(),
          currency: this.planCurrency(), roomTypeId: this.planRoomTypeId(), isActive: this.planIsActive(),
        })
      : this.api.createRatePlan({
          propId: current.propId, name: this.planName(), description: this.planDescription(),
          baseRate: this.planBaseRate(), currency: this.planCurrency(), roomTypeId: this.planRoomTypeId(), isActive: this.planIsActive(),
        });
    obs.pipe(
      switchMap(() => this.api.getRates(current.propId)),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (rates) => {
        this.viewModel.set(rates);
        this.message.set('Plan tarifario registrado'); this.errorMessage.set('');
        this.editingPlan.set(null);
        this.planName.set(''); this.planDescription.set(''); this.planBaseRate.set(0); this.planCurrency.set('USD'); this.planRoomTypeId.set(''); this.planIsActive.set(true);
      },
      error: (error: ApiError) => { this.errorMessage.set(error.message || 'No fue posible registrar el plan tarifario.'); this.message.set(''); },
    });
  }

  onEditPlan(plan: any): void {
    this.editingPlan.set({
      id: plan.id, name: plan.name, description: plan.description, baseRate: plan.baseRate,
      currency: plan.currency, roomTypeId: plan.roomTypeId ?? '', isActive: plan.activeLabel === 'Sí',
    });
    this.planName.set(plan.name); this.planDescription.set(plan.description); this.planBaseRate.set(plan.baseRate);
    this.planCurrency.set(plan.currency); this.planRoomTypeId.set(plan.roomTypeId ?? ''); this.planIsActive.set(plan.activeLabel === 'Sí');
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParamsHandling: 'merge',
      queryParams: { section: 'plans' },
    });
    setTimeout(() => document.querySelector('.plan-form-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
  }

  cancelEditPlan(): void {
    this.editingPlan.set(null);
    this.planName.set(''); this.planDescription.set(''); this.planBaseRate.set(0); this.planCurrency.set('USD'); this.planRoomTypeId.set(''); this.planIsActive.set(true);
  }

  onDeletePlan(planId: string): void { this.deleteConfirm.set(planId); }

  confirmDeletePlan(): void {
    const planId = this.deleteConfirm(); if (!planId) return;
    this.deleteConfirm.set(null);
    const current = this.viewModel(); if (!current) return;
    this.api.deleteRatePlan(planId).pipe(
      switchMap(() => this.api.getRates(current.propId)),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (rates) => { this.viewModel.set(rates); this.message.set('Plan tarifario eliminado'); this.errorMessage.set(''); },
      error: (error: ApiError) => { this.errorMessage.set(error.message || 'Error al eliminar plan.'); this.message.set(''); },
    });
  }

  /* ── Calendar Entry ── */
  saveRate(): void {
    const current = this.viewModel();
    if (!current || !this.calendarRatePlanId() || !this.calendarDate() || this.calendarRateAmount() <= 0) { return; }
    this.api.saveRate({
      propId: current.propId, ratePlanId: this.calendarRatePlanId(), date: this.calendarDate(),
      rateAmount: this.calendarRateAmount(), minStayNights: this.calendarMinStayNights(), isClosed: this.calendarIsClosed(),
    }).pipe(
      switchMap(() => this.api.getRates(current.propId)),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (rates) => { this.viewModel.set(rates); this.message.set('Tarifa actualizada'); this.errorMessage.set(''); this.calendarRatePlanId.set(''); this.calendarDate.set(''); this.calendarRateAmount.set(0); this.calendarMinStayNights.set(1); this.calendarIsClosed.set(false); },
      error: (error: ApiError) => { this.errorMessage.set(error.message || 'No fue posible actualizar la tarifa.'); this.message.set(''); },
    });
  }

  /* ── Batch Update ── */
  batchUpdateCalendar(): void {
    const current = this.viewModel();
    if (!current || !this.batchRatePlanId() || !this.batchStartDate() || !this.batchEndDate() || this.batchRateAmount() <= 0) { return; }
    this.api.batchUpdateCalendar({
      propId: current.propId, ratePlanId: this.batchRatePlanId(), startDate: this.batchStartDate(),
      endDate: this.batchEndDate(), rateAmount: this.batchRateAmount(), minStayNights: this.batchMinStayNights() || undefined, onlyWeekends: this.batchOnlyWeekends(),
    }).pipe(
      switchMap(() => this.api.getRates(current.propId)),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (rates) => { this.viewModel.set(rates); this.message.set('Calendario actualizado por lote'); this.errorMessage.set(''); this.batchRatePlanId.set(''); this.batchStartDate.set(''); this.batchEndDate.set(''); this.batchRateAmount.set(0); this.batchMinStayNights.set(1); this.batchOnlyWeekends.set(false); },
      error: (error: ApiError) => { this.errorMessage.set(error.message || 'Error al actualizar calendario por lote.'); this.message.set(''); },
    });
  }

  /* ── Generate Calendar ── */
  generateCalendar(): void {
    const current = this.viewModel();
    if (!current) return;
    this.api.generateCalendar({
      propId: current.propId, ratePlanId: this.generateRatePlanId() || undefined,
      startDate: this.generateStartDate() || undefined, endDate: this.generateEndDate() || undefined,
    }).pipe(
      switchMap((result) => { this.message.set(`Calendario generado: ${result.entries_generated} entradas`); return this.api.getRates(current.propId); }),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (rates) => { this.viewModel.set(rates); this.errorMessage.set(''); this.generateRatePlanId.set(''); this.generateStartDate.set(''); this.generateEndDate.set(''); },
      error: (error: ApiError) => { this.errorMessage.set(error.message || 'Error al generar calendario.'); this.message.set(''); },
    });
  }

  /* ── Seasonal Rules ── */
  createSeasonalRule(): void {
    const current = this.viewModel();
    if (!current || !this.seasonalRatePlanId() || !this.seasonalName() || !this.seasonalStartDate() || !this.seasonalEndDate() || this.seasonalPriceOverride() <= 0) { return; }
    this.api.createSeasonalRule({
      propId: current.propId, ratePlanId: this.seasonalRatePlanId(), name: this.seasonalName(),
      startDate: this.seasonalStartDate(), endDate: this.seasonalEndDate(), priceOverride: this.seasonalPriceOverride(),
    }).pipe(
      switchMap(() => this.api.getRates(current.propId)),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (rates) => { this.viewModel.set(rates); this.message.set('Regla de temporada creada'); this.errorMessage.set(''); this.seasonalRatePlanId.set(''); this.seasonalName.set(''); this.seasonalStartDate.set(''); this.seasonalEndDate.set(''); this.seasonalPriceOverride.set(0); },
      error: (error: ApiError) => { this.errorMessage.set(error.message || 'Error al crear regla de temporada.'); this.message.set(''); },
    });
  }

  deleteSeasonalRule(ruleId: string): void {
    const current = this.viewModel(); if (!current) return;
    this.api.deleteSeasonalRule(ruleId).pipe(
      switchMap(() => this.api.getRates(current.propId)),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (rates) => { this.viewModel.set(rates); this.message.set('Regla de temporada eliminada'); },
      error: (error: ApiError) => { this.errorMessage.set(error.message || 'Error al eliminar regla de temporada.'); },
    });
  }

  /* ── Promotions ── */
  refreshAfterPromo(): void {
    const current = this.viewModel(); if (!current) return;
    forkJoin({
      rates: this.api.getRates(current.propId),
      promotions: this.api.listPropertyPromotions(current.propId),
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: ({ rates, promotions }) => { this.viewModel.set(rates); this.promotionsData.set(promotions); },
    });
  }

  onTogglePromo(campaignId: string): void {
    const current = this.viewModel(); if (!current) return;
    this.api.togglePromotion(campaignId).pipe(
      switchMap(() => forkJoin({ rates: this.api.getRates(current.propId), promotions: this.api.listPropertyPromotions(current.propId) })),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: ({ rates, promotions }) => { this.viewModel.set(rates); this.promotionsData.set(promotions); this.message.set('Estado de promoción actualizado'); this.errorMessage.set(''); },
      error: (error: ApiError) => { this.errorMessage.set(error.message || 'Error al cambiar estado.'); this.message.set(''); },
    });
  }

  onDeletePromo(campaignId: string): void { this.promoDeleteConfirm.set(campaignId); }

  confirmDeletePromo(): void {
    const campaignId = this.promoDeleteConfirm(); if (!campaignId) return;
    this.promoDeleteConfirm.set(null);
    const current = this.viewModel(); if (!current) return;
    this.api.updatePromotion(campaignId, { isActive: false }).pipe(
      switchMap(() => forkJoin({ rates: this.api.getRates(current.propId), promotions: this.api.listPropertyPromotions(current.propId) })),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: ({ rates, promotions }) => { this.viewModel.set(rates); this.promotionsData.set(promotions); this.message.set('Promoción desactivada'); this.errorMessage.set(''); },
      error: (error: ApiError) => { this.errorMessage.set(error.message || 'Error al desactivar promoción.'); this.message.set(''); },
    });
  }

  onEditPromo(promo: any): void {
    this.editingPromo.set({
      campaignId: promo.campaignId,
      name: promo.name,
      description: promo.description || '',
      discountPercent: promo.discountPercent,
      couponCount: promo.couponTotal ?? 0,
      startDate: promo.startDate || '',
      endDate: promo.endDate || '',
      isActive: promo.isActive,
    });
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParamsHandling: 'merge',
      queryParams: { section: 'promos' },
    });
  }
}
