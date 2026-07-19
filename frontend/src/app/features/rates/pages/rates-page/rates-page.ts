import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import type { PromoEditState } from '../../components/promotion-form/promotion-form';
import { httpResource } from '@angular/common/http';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { KpiChartComponent } from '../../../../shared/ui/kpi-chart/kpi-chart';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import type { RatePlanOption, RatesViewModel } from '../../models/rates.model';
import type { RatesDto } from '../../models/rates.dto';
import { RatesApiService } from '../../services/rates-api.service';
import { mapRatesResponse } from '../../mappers/rates.mapper';
import { KpiApiService, type RateTrendResponse } from '../../../../shared/services/kpi-api.service';
import { RatePlanTableComponent } from '../../components/rate-plan-table/rate-plan-table';
import { RateCalendarTableComponent } from '../../components/rate-calendar-table/rate-calendar-table';
import { RateSidebarComponent, type SidebarSection } from '../../components/rate-sidebar/rate-sidebar';
import { RateKpiGridComponent, type KpiData } from '../../components/rate-kpi-grid/rate-kpi-grid';
import { RateMonthlyCalendarComponent, type RoomTypeCalendarRow } from '../../components/rate-monthly-calendar/rate-monthly-calendar';
import { PromotionFormComponent } from '../../components/promotion-form/promotion-form';
import { PromotionsTableComponent, type CampaignRow, type CouponRow } from '../../components/promotions-table/promotions-table';
import { SeasonalRulesTableComponent, type SeasonalRuleRow } from '../../components/seasonal-rules-table/seasonal-rules-table';

import { AiSuggestDirective } from '../../../../core/directives/ai-suggest.directive';

/** Return the Monday of the week containing the given date. */
function _mondayOfWeek(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

@Component({
  selector: 'app-rates-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    KpiChartComponent,
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
  private readonly kpiApi = inject(KpiApiService);
  private readonly destroyRef = inject(DestroyRef);
  readonly propertyCtx = inject(PropertyContextService);

  // ── KPI: 7-day rate trend ──
  readonly rateTrend = signal<RateTrendResponse | null>(null);
  readonly rateTrendState = signal<'loading' | 'success' | 'error'>('loading');

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
  readonly ratesResource = httpResource<RatesViewModel>(() => {
    const propId = this.routePropId();
    return propId > 0 ? `/api/management/rates?prop_id=${propId}` : undefined;
  }, {
    parse: (res) => mapRatesResponse(res as RatesDto),
  });

  /* ── State ── */
  readonly viewState = signal<ViewState>('loading');

  /** Derived from ratesResource — no separate API call needed. */
  readonly ratePlanOptions = computed<RatePlanOption[]>(() =>
    (this.ratesResource.value()?.ratePlans ?? []).map((p) => ({ id: p.id, label: p.name }))
  );
  /** Calendar items for overview table — today+future by default, all dates when showPastDates is on. */
  readonly overviewCalendarItems = computed<import('../../models/rates.model').RateCalendarItem[]>(() => {
    const items = this.ratesResource.value()?.calendar ?? [];
    if (this.showPastDates()) return items;
    const today = new Date().toISOString().slice(0, 10);
    return items.filter((c) => c.date >= today);
  });
  /** Toggle to show/hide past dates in the overview calendar */
  readonly showPastDates = signal(false);

  readonly message = signal('');
  readonly errorMessage = signal('');

  /** Current property ID — derived from URL (source of truth). */
  readonly selectedPropId = computed(() => this.routePropId());

  /** Current property name — derived from loaded data. */
  readonly selectedLabel = computed(() => this.ratesResource.value()?.hotelLabel ?? '');

  /** Current section — derived from URL query param. */
  readonly activeSection = computed(() => this.routeSection());
  readonly editingPlan = signal<{ id: string; name: string; description: string; baseRate: number; currency: string; applicableRoomTypes: string[]; isActive: boolean } | null>(null);
  readonly editingSeason = signal<{ ruleId: string; ratePlanId: string; name: string; startDate: string; endDate: string; priceOverride: number } | null>(null);
  readonly deleteConfirm = signal<string | null>(null);
  readonly promoDeleteConfirm = signal<string | null>(null);
  readonly promotionsData = signal<{ campaigns: any[]; total: number } | null>(null);
  readonly editingPromo = signal<PromoEditState | null>(null);

  /* ── Form signals (replacing FormBuilder) ── */

  // Plan form
  readonly planName = signal('');
  readonly planDescription = signal('');
  /** Applicable room types — multi-select via checkbox grid. */
  readonly planApplicableRoomTypes = signal<string[]>([]);

  togglePlanRoomType(roomTypeId: string): void {
    this.planApplicableRoomTypes.update((current) => {
      const exists = current.includes(roomTypeId);
      return exists ? current.filter((id) => id !== roomTypeId) : [...current, roomTypeId];
    });
  }
  readonly planBaseRate = signal(0);
  readonly planCurrency = signal('USD');
  readonly planIsActive = signal(true);
  readonly planIncludedAmenities = signal<string[]>([]);

  /** Amenity catalog loaded from API — all available amenity labels for this property. */
  readonly amenityCatalog = signal<{ category: string; label: string; unit_price: number; active: boolean }[]>([]);

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
  readonly seasonalPriceTouched = signal(false);

  // Collapsible sections (collapsed by default)
  readonly batchCalendarCollapsed = signal(true);
  readonly planFormCollapsed = signal(false);
  readonly existingPlansCollapsed = signal(false);
  readonly newSeasonalCollapsed = signal(false);
  readonly existingSeasonsCollapsed = signal(false);

  toggleCollapse(section: string): void {
    if (section === 'planForm') this.planFormCollapsed.update(v => !v);
    else if (section === 'existingPlans') this.existingPlansCollapsed.update(v => !v);
    else if (section === 'newSeasonal') this.newSeasonalCollapsed.update(v => !v);
    else if (section === 'existingSeasons') this.existingSeasonsCollapsed.update(v => !v);
    else if (section === 'batchCalendar') this.batchCalendarCollapsed.update(v => !v);
  }

  /* ── Sidebar sections ── */
readonly sidebarSections: SidebarSection[] = [
  { id: 'overview', label: 'Panel', icon: 'dashboard' },
  { id: 'rate-entry', label: 'Entrada Individual', icon: 'edit_calendar' },
  { id: 'calendar', label: 'Calendario Global', icon: 'calendar_month' },
  { id: 'plans', label: 'Planes Tarifarios', icon: 'table' },
  { id: 'seasons', label: 'Temporadas', icon: 'event' },
  { id: 'promos', label: 'Promociones', icon: 'campaign' },
];

  /* ── KPI data derived from ratesResource ── */
  readonly kpiData = computed((): KpiData | null => {
    const vm = this.ratesResource.value();
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

  /* ── Calendar data derived from ratesResource ── */
  readonly calendarMonth = signal(new Date().getMonth());
  readonly calendarYear = signal(new Date().getFullYear());

  /** Display mode for calendar: 'month' (full month) or 'week' (7 days). */
  readonly calendarDisplayMode = signal<'month' | 'week'>('week');
  /** Week anchor: Monday Date for week view. */
  readonly weekAnchor = signal<Date>(_mondayOfWeek(new Date()));

  /** Extract short room "number" from room_type_id (strip 'RT-{prop_id}-' prefix). */
  _roomNumber(rtId: string): string {
    const vm = this.ratesResource.value();
    if (!vm) return rtId;
    const prefix = `RT-${vm.propId}-`;
    return rtId.startsWith(prefix) ? rtId.slice(prefix.length) : rtId;
  }

  readonly calendarRows = computed((): RoomTypeCalendarRow[] => {
    const vm = this.ratesResource.value();
    if (!vm) return [];
    const month = this.calendarMonth();
    const year = this.calendarYear();
    const mode = this.calendarDisplayMode();

    // Date filter based on mode
    let dateFilter: (dateStr: string) => boolean;
    if (mode === 'month') {
      const monthStr = `${year}-${String(month + 1).padStart(2, '0')}`;
      dateFilter = (d) => d.startsWith(monthStr);
    } else {
      // Week view: get the Monday anchor and create 7-day window
      const anchor = this.weekAnchor();
      const dates: string[] = [];
      for (let i = 0; i < 7; i++) {
        const d = new Date(anchor);
        d.setDate(anchor.getDate() + i);
        dates.push(d.toISOString().slice(0, 10));
      }
      dateFilter = (d) => dates.includes(d);
    }

    // Rate plan → applicable room types: N:N mapping
    // Build a Set<ratePlanId> per room type for O(1) lookup
    const roomTypePlanIds = new Map<string, Set<string>>();
    for (const plan of vm.ratePlans) {
      const rtIds = plan.applicableRoomTypes ?? (plan.roomTypeId ? [plan.roomTypeId] : []);
      for (const rtId of rtIds) {
        if (!roomTypePlanIds.has(rtId)) {
          roomTypePlanIds.set(rtId, new Set());
        }
        roomTypePlanIds.get(rtId)!.add(plan.id);
      }
    }

    return vm.roomTypes.map((rt) => ({
      roomTypeId: rt.id,
      roomTypeName: rt.name,
      roomTypeNumber: this._roomNumber(rt.id),
      days: vm.calendar
        .filter((c) => roomTypePlanIds.get(rt.id)?.has(c.ratePlanId) && dateFilter(c.date))
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

  /** Events derived from seasonal rules and promotions for the displayed dates. */
  readonly calendarEvents = computed(() => {
    const vm = this.ratesResource.value();
    if (!vm) return [];
    const events: { date: string; type: 'season' | 'promo' | 'batch' | 'rate_entry'; label: string; color: string }[] = [];

    // Seasonal rules → events per date in range
    for (const rule of vm.seasonalRules) {
      if (rule.startDate && rule.endDate) {
        const start = new Date(rule.startDate);
        const end = new Date(rule.endDate);
        const cur = new Date(start);
        while (cur <= end) {
          const dateStr = cur.toISOString().slice(0, 10);
          events.push({
            date: dateStr,
            type: 'season',
            label: rule.name,
            color: '#8b5cf6',
          });
          cur.setDate(cur.getDate() + 1);
        }
      }
    }

    // Promotions → events per date in range
    for (const promo of vm.promotions) {
      const parts = promo.dateRange.split(' → ');
      if (parts.length === 2 && parts[0] && parts[1]) {
        const start = new Date(parts[0]);
        const end = new Date(parts[1]);
        const cur = new Date(start);
        while (cur <= end) {
          const dateStr = cur.toISOString().slice(0, 10);
          events.push({
            date: dateStr,
            type: 'promo',
            label: promo.name || 'Promoción',
            color: '#d97706',
          });
          cur.setDate(cur.getDate() + 1);
        }
      }
    }

    return events;
  });

  /* ── Derived data for tables ── */
  readonly seasonalRuleRows = computed((): SeasonalRuleRow[] => {
    return (this.ratesResource.value()?.seasonalRules ?? []).map((r) => ({
      ruleId: r.ruleId,
      name: r.name,
      ratePlanId: r.ratePlanId,
      startDate: r.startDate,
      endDate: r.endDate,
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
    return (this.ratesResource.value()?.promotions ?? []).map((p) => ({
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
    return (this.ratesResource.value()?.coupons ?? []).map((c) => ({
      code: c.code,
      activeLabel: c.activeLabel,
    }));
  });


  get roomTypes() { return this.ratesResource.value()?.roomTypes ?? []; }

  /** Map of room_type_id → short room number for the plan table. */
  readonly roomTypeNumberMap = computed<Record<string, string>>(() => {
    const vm = this.ratesResource.value();
    if (!vm) return {};
    const map: Record<string, string> = {};
    for (const rt of vm.roomTypes) {
      map[rt.id] = this._roomNumber(rt.id);
    }
    return map;
  });

  constructor() {
    // Load 7-day rate trend
    this.kpiApi.getRateTrend(5).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (res) => { this.rateTrend.set(res); this.rateTrendState.set('success'); },
      error: () => this.rateTrendState.set('error'),
    });

    // ── Load amenity catalog when prop changes ──
    effect(() => {
      const propId = this.selectedPropId();
      if (!propId) { return; }
      this.api.getAmenityCatalog(propId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (catalog) => this.amenityCatalog.set(catalog),
        error: () => this.amenityCatalog.set([]),
      });
    });

    // ── Sync httpResource → viewState + property context ──
    effect(() => {
      const propId = this.selectedPropId();

      if (!propId) {
        this.viewState.set('empty');
        this.message.set('');
        this.errorMessage.set('');
        this.editingPlan.set(null);
        this.editingPromo.set(null);
        this.deleteConfirm.set(null);
        this.propertyCtx.clear();
        return;
      }

      if (this.ratesResource.isLoading()) {
        this.viewState.set(this.ratesResource.value() ? 'success' : 'loading');
        return;
      }

      if (this.ratesResource.error()) {
        this.viewState.set('error');
        this.errorMessage.set('No se pudo cargar la información.');
        return;
      }

      const data = this.ratesResource.value();
      if (data) {
        this.viewState.set('success');
        this.errorMessage.set('');
        this.propertyCtx.setProperty(data.propId, data.hotelLabel);
      }      }, { allowSignalWrites: true });

    // Auto-carga en modo single-hotel: si no hay prop_id en URL pero el contexto
    // está ready, navegar con el propId del contexto
    effect(() => {
      if (this.propertyCtx.ready() && this.propertyCtx.singleHotelMode()) {
        const propId = this.propertyCtx.currentPropId();
        if (propId && !this.routePropId()) {
          void this.router.navigate([], {
            relativeTo: this.route,
            queryParams: { prop_id: propId },
          });
        }
      }
    });
  }

  onPropSelected(event: { propId: number; label: string }): void {
    if (!event.propId) this.propertyCtx.clear();
    const label = event.label || `Propiedad #${event.propId}`;
    this.propertyCtx.setProperty(event.propId, label);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null, prop_label: label || null },
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
    if (this.calendarDisplayMode() === 'week') {
      // In week mode: navigate by 7 days based on direction
      const oldTotal = this.calendarYear() * 12 + this.calendarMonth();
      const newTotal = year * 12 + month;
      const direction = newTotal > oldTotal ? 1 : -1;
      const anchor = new Date(this.weekAnchor());
      anchor.setDate(anchor.getDate() + 7 * direction);
      this.weekAnchor.set(anchor);
      this.calendarMonth.set(anchor.getMonth());
      this.calendarYear.set(anchor.getFullYear());
    } else {
      this.calendarMonth.set(month);
      this.calendarYear.set(year);
    }
  }

  /* ── Rate Plan CRUD ── */
  /** Toggle an amenity label in the planIncludedAmenities signal. */
  togglePlanAmenity(label: string): void {
    this.planIncludedAmenities.update((current) => {
      const exists = current.includes(label);
      return exists ? current.filter((a) => a !== label) : [...current, label];
    });
  }

  /** Flatten the amenity catalog into unique labels grouped by category for the UI. */
  readonly amenityGroups = computed(() => {
    const catalog = this.amenityCatalog();
    const groups = new Map<string, { label: string; unitPrice: number }[]>();
    for (const item of catalog) {
      const cat = item.category || 'General';
      if (!groups.has(cat)) { groups.set(cat, []); }
      groups.get(cat)!.push({ label: item.label, unitPrice: item.unit_price });
    }
    return Array.from(groups.entries()).map(([category, items]) => ({ category, items }));
  });

  createRatePlan(): void {
    const current = this.ratesResource.value();
    if (!current || !this.planName() || this.planBaseRate() <= 0) { return; }
    const obs = this.editingPlan()
      ? this.api.updateRatePlan(this.editingPlan()!.id, {
          name: this.planName(), description: this.planDescription(), baseRate: this.planBaseRate(),
          currency: this.planCurrency(), applicableRoomTypes: this.planApplicableRoomTypes(), isActive: this.planIsActive(),
          includedAmenities: this.planIncludedAmenities(),
        })
      : this.api.createRatePlan({
          propId: current.propId, name: this.planName(), description: this.planDescription(),
          baseRate: this.planBaseRate(), currency: this.planCurrency(), applicableRoomTypes: this.planApplicableRoomTypes(), isActive: this.planIsActive(),
          includedAmenities: this.planIncludedAmenities(),
        });
    obs.pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: () => {
        this.ratesResource.reload();
        this.message.set('Plan tarifario registrado'); this.errorMessage.set('');
        this.editingPlan.set(null);
        this.planName.set(''); this.planDescription.set(''); this.planBaseRate.set(0); this.planCurrency.set('USD'); this.planApplicableRoomTypes.set([]); this.planIsActive.set(true); this.planIncludedAmenities.set([]);
      },
      error: (error: ApiError) => { this.errorMessage.set(error.message || 'No fue posible registrar el plan tarifario.'); this.message.set(''); },
    });
  }

  onEditPlan(plan: any): void {
    this.editingPlan.set({
      id: plan.id, name: plan.name, description: plan.description, baseRate: plan.baseRate,
      currency: plan.currency, applicableRoomTypes: plan.applicableRoomTypes ?? [], isActive: plan.activeLabel === 'Sí',
    });
    this.planName.set(plan.name); this.planDescription.set(plan.description); this.planBaseRate.set(plan.baseRate);
    this.planCurrency.set(plan.currency); this.planApplicableRoomTypes.set(plan.applicableRoomTypes ?? []); this.planIsActive.set(plan.activeLabel === 'Sí');
    this.planIncludedAmenities.set(plan.includedAmenities ?? []);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParamsHandling: 'merge',
      queryParams: { section: 'plans' },
    });
    setTimeout(() => document.querySelector('.plan-form-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
  }

  cancelEditPlan(): void {
    this.editingPlan.set(null);
    this.planName.set(''); this.planDescription.set(''); this.planBaseRate.set(0); this.planCurrency.set('USD'); this.planApplicableRoomTypes.set([]); this.planIsActive.set(true);
    this.planIncludedAmenities.set([]);
  }

  onDeletePlan(planId: string): void { this.deleteConfirm.set(planId); }

  confirmDeletePlan(): void {
    const planId = this.deleteConfirm(); if (!planId) return;
    this.deleteConfirm.set(null);
    const current = this.ratesResource.value(); if (!current) return;
    this.api.deleteRatePlan(planId).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: () => { this.ratesResource.reload(); this.message.set('Plan tarifario eliminado'); this.errorMessage.set(''); },
      error: (error: ApiError) => { this.errorMessage.set(error.message || 'Error al eliminar plan.'); this.message.set(''); },
    });
  }

  /* ── Calendar Entry ── */
  saveRate(): void {
    const current = this.ratesResource.value();
    if (!current || !this.calendarRatePlanId() || !this.calendarDate() || this.calendarRateAmount() <= 0) { return; }
    this.api.saveRate({
      propId: current.propId, ratePlanId: this.calendarRatePlanId(), date: this.calendarDate(),
      rateAmount: this.calendarRateAmount(), minStayNights: this.calendarMinStayNights(), isClosed: this.calendarIsClosed(),
    }).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: () => { this.ratesResource.reload(); this.message.set('Tarifa actualizada'); this.errorMessage.set(''); this.calendarRatePlanId.set(''); this.calendarDate.set(''); this.calendarRateAmount.set(0); this.calendarMinStayNights.set(1); this.calendarIsClosed.set(false); },
      error: (error: ApiError) => { this.errorMessage.set(error.message || 'No fue posible actualizar la tarifa.'); this.message.set(''); },
    });
  }

  /* ── Batch Update ── */
  batchUpdateCalendar(): void {
    const current = this.ratesResource.value();
    if (!current || !this.batchRatePlanId() || !this.batchStartDate() || !this.batchEndDate() || this.batchRateAmount() <= 0) { return; }
    if (this.batchStartDate() > this.batchEndDate()) {
      this.errorMessage.set('La fecha de inicio no puede ser mayor a la fecha de fin.');
      return;
    }
    this.api.batchUpdateCalendar({
      propId: current.propId, ratePlanId: this.batchRatePlanId(), startDate: this.batchStartDate(),
      endDate: this.batchEndDate(), rateAmount: this.batchRateAmount(), minStayNights: this.batchMinStayNights() || undefined, onlyWeekends: this.batchOnlyWeekends(),
    }).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: () => { this.ratesResource.reload(); this.message.set('Calendario actualizado por lote'); this.errorMessage.set(''); this.batchRatePlanId.set(''); this.batchStartDate.set(''); this.batchEndDate.set(''); this.batchRateAmount.set(0); this.batchMinStayNights.set(1); this.batchOnlyWeekends.set(false); },
      error: (error: ApiError) => { this.errorMessage.set(error.message || 'Error al actualizar calendario por lote.'); this.message.set(''); },
    });
  }

  /* ── Generate Calendar ── */
  generateCalendar(): void {
    const current = this.ratesResource.value();
    if (!current) return;
    if (this.generateStartDate() && this.generateEndDate() && this.generateStartDate() > this.generateEndDate()) {
      this.errorMessage.set('La fecha de inicio no puede ser mayor a la fecha de fin.');
      return;
    }
    this.api.generateCalendar({
      propId: current.propId, ratePlanId: this.generateRatePlanId() || undefined,
      startDate: this.generateStartDate() || undefined, endDate: this.generateEndDate() || undefined,
    }).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (result) => {
        this.ratesResource.reload();
        this.message.set(`Calendario generado: ${result.entries_generated} entradas`);
        this.errorMessage.set('');
        this.generateRatePlanId.set(''); this.generateStartDate.set(''); this.generateEndDate.set('');
      },
      error: (error: ApiError) => { this.errorMessage.set(error.message || 'Error al generar calendario.'); this.message.set(''); },
    });
  }

  /* ── Seasonal Rules ── */
  onEditSeason(rule: SeasonalRuleRow): void {
    this.editingSeason.set({
      ruleId: rule.ruleId,
      ratePlanId: rule.ratePlanId,
      name: rule.name,
      startDate: rule.startDate,
      endDate: rule.endDate,
      priceOverride: rule.priceOverride,
    });
    this.seasonalRatePlanId.set(rule.ratePlanId);
    this.seasonalName.set(rule.name);
    this.seasonalStartDate.set(rule.startDate);
    this.seasonalEndDate.set(rule.endDate);
    this.seasonalPriceOverride.set(rule.priceOverride);
    this.newSeasonalCollapsed.set(false);
  }

  cancelEditSeason(): void {
    this.editingSeason.set(null);
    this.seasonalRatePlanId.set('');
    this.seasonalName.set('');
    this.seasonalStartDate.set('');
    this.seasonalEndDate.set('');
    this.seasonalPriceOverride.set(0);
  }

  createSeasonalRule(): void {
    const current = this.ratesResource.value();
    this.seasonalPriceTouched.set(true);
    if (!current || !this.seasonalRatePlanId() || !this.seasonalName() || !this.seasonalStartDate() || !this.seasonalEndDate()) {
      this.errorMessage.set('Completa todos los campos requeridos.');
      return;
    }
    if (this.seasonalPriceOverride() <= 0) {
      this.errorMessage.set('El precio override debe ser mayor a 0.');
      return;
    }
    if (this.seasonalStartDate() > this.seasonalEndDate()) {
      this.errorMessage.set('La fecha de inicio no puede ser mayor a la fecha de fin.');
      return;
    }

    const edit = this.editingSeason();

    const obs = edit
      ? this.api.updateSeasonalRule(edit.ruleId, {
          ratePlanId: this.seasonalRatePlanId(),
          name: this.seasonalName(),
          startDate: this.seasonalStartDate(),
          endDate: this.seasonalEndDate(),
          priceOverride: this.seasonalPriceOverride(),
        })
      : this.api.createSeasonalRule({
          propId: current.propId,
          ratePlanId: this.seasonalRatePlanId(),
          name: this.seasonalName(),
          startDate: this.seasonalStartDate(),
          endDate: this.seasonalEndDate(),
          priceOverride: this.seasonalPriceOverride(),
        });

    obs.pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: () => {
        this.ratesResource.reload();
        this.message.set(edit ? 'Regla de temporada actualizada' : 'Regla de temporada creada');
        this.errorMessage.set('');
        this.cancelEditSeason();
      },
      error: (error: ApiError) => { this.errorMessage.set(error.message || 'Error al guardar regla de temporada.'); this.message.set(''); },
    });
  }

  deleteSeasonalRule(ruleId: string): void {
    const current = this.ratesResource.value(); if (!current) return;
    this.api.deleteSeasonalRule(ruleId).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: () => { this.ratesResource.reload(); this.message.set('Regla de temporada eliminada'); },
      error: (error: ApiError) => { this.errorMessage.set(error.message || 'Error al eliminar regla de temporada.'); },
    });
  }

  /* ── Promotions ── */
  refreshAfterPromo(): void {
    const current = this.ratesResource.value(); if (!current) return;
    this.ratesResource.reload();
    this.api.listPropertyPromotions(current.propId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (promotions) => { this.promotionsData.set(promotions); },
      error: () => { this.errorMessage.set('Error al recargar promociones.'); },
    });
  }

  onTogglePromo(campaignId: string): void {
    const current = this.ratesResource.value(); if (!current) return;
    this.api.togglePromotion(campaignId).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: () => {
        this.ratesResource.reload();
        this.api.listPropertyPromotions(current.propId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
          next: (promotions) => { this.promotionsData.set(promotions); this.message.set('Estado de promoción actualizado'); this.errorMessage.set(''); },
          error: () => { this.errorMessage.set('Error al recargar promociones.'); },
        });
      },
      error: (error: ApiError) => { this.errorMessage.set(error.message || 'Error al cambiar estado.'); this.message.set(''); },
    });
  }

  onDeletePromo(campaignId: string): void { this.promoDeleteConfirm.set(campaignId); }

  confirmDeletePromo(): void {
    const campaignId = this.promoDeleteConfirm(); if (!campaignId) return;
    this.promoDeleteConfirm.set(null);
    const current = this.ratesResource.value(); if (!current) return;
    this.api.updatePromotion(campaignId, { isActive: false }).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: () => {
        this.ratesResource.reload();
        this.api.listPropertyPromotions(current.propId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
          next: (promotions) => { this.promotionsData.set(promotions); this.message.set('Promoción desactivada'); this.errorMessage.set(''); },
          error: () => { this.errorMessage.set('Error al recargar promociones.'); },
        });
      },
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
