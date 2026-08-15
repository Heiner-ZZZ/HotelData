import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { KpiChartComponent } from '../../../../shared/ui/kpi-chart/kpi-chart';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { mapPolicies, mapPoliciesPayload } from '../../mappers/policies.mapper';
import type { PoliciesViewModel } from '../../models/policies.model';
import type { PoliciesDto } from '../../models/policies.dto';
import { PoliciesApiService } from '../../services/policies-api.service';
import { KpiApiService, type OccupancyTrendResponse, type OperationalStatsResponse } from '../../../../shared/services/kpi-api.service';
import { PolicySummaryCardsComponent } from '../../components/policy-summary-cards/policy-summary-cards';
import { AiSuggestDirective } from '../../../../core/directives/ai-suggest.directive';
import { ModeHighlightDirective } from '../../../../core/directives/mode-highlight.directive';
import { ToastService } from '../../../../shared/services/toast.service';
import { InfoTooltipComponent } from '../../../../shared/ui/info-tooltip/info-tooltip.component';

@Component({
  selector: 'app-policies-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    KpiChartComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    InfoTooltipComponent,
    PolicySummaryCardsComponent,
    PropertySelectorComponent,
    ReactiveFormsModule,
    AiSuggestDirective,
    ModeHighlightDirective,
  ],
  templateUrl: './policies-page.html',
  styleUrl: './policies-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PoliciesPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(PoliciesApiService);
  private readonly kpiApi = inject(KpiApiService);
  private readonly toast = inject(ToastService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  readonly propertyCtx = inject(PropertyContextService);
  private readonly opMode = inject(OperationModeService);

  // ── KPI: Operational stats ──
  readonly opStats = signal<OperationalStatsResponse | null>(null);
  readonly opStatsState = signal<'loading' | 'success' | 'error'>('loading');

  // ── KPI: Occupancy trend (line chart, hidden when hotel selected) ──
  readonly occupancyTrend = signal<OccupancyTrendResponse | null>(null);

  readonly selectedPropId = signal(0);
  readonly selectedRoomTypeId = signal('');
  readonly selectedRatePlanId = signal('');

  readonly policiesResource = httpResource<PoliciesViewModel>(() => {
    const propId = this.selectedPropId();
    if (!propId) return undefined;
    const roomTypeId = this.selectedRoomTypeId();
    const ratePlanId = this.selectedRatePlanId();
    const rtParam = roomTypeId ? '&room_type_id=' + roomTypeId : '';
    const rpParam = ratePlanId ? '&rate_plan_id=' + ratePlanId : '';
    return `/api/management/policies?prop_id=${propId}${rtParam}${rpParam}`;
  }, {
    parse: (dto) => mapPolicies(dto as PoliciesDto),
  });

  readonly viewState = computed<ViewState>(() => {
    if (this.policiesResource.isLoading()) return 'loading';
    if (this.policiesResource.error()) return 'error';
    const vm = this.policiesResource.value();
    if (!vm) return 'empty';
    return 'success';
  });

  readonly selectedLabel = computed(() => this.policiesResource.value()?.hotelName ?? '');
  readonly roomTypeOptions = computed(() => this.policiesResource.value()?.roomTypes ?? []);

  /** Rate plan options — derived from policies resource (backend now includes them). */
  readonly ratePlanOptions = computed(() => this.policiesResource.value()?.ratePlanOptions ?? []);

  /** Hotel-level check-in/check-out — never overridden by room-type policies. */
  private hotelCheckInTime = '';
  private hotelCheckOutTime = '';

  // ═══ Explicit editing mode (mode-aware UI) ═══
  /** True while the user is actively editing policies. */
  readonly editing = signal(false);
  /** Snapshot of the persisted form values when the edit session began. */
  private baseFormValue: Record<string, string | number | boolean> | null = null;
  /** Last vm applied to the form — guards against re-applying a stale resource
      value while a post-save reload is still in flight. */
  private lastAppliedVm: PoliciesViewModel | null = null;

  /** Any pending change vs. the snapshot taken when editing began. */
  readonly dirty = computed(() => {
    if (!this.editing() || !this.baseFormValue) return false;
    const base = this.baseFormValue;
    const cur = this.policyForm.getRawValue() as unknown as Record<string, string | number | boolean>;
    return Object.keys(base).some((key) => base[key] !== cur[key]);
  });

  /** Start an edit session: snapshot current values and switch the nav chip to "update". */
  startEditing(): void {
    if (this.editing()) return;
    this.baseFormValue = { ...this.policyForm.getRawValue() } as Record<string, string | number | boolean>;
    this.editing.set(true);
    this.policyForm.enable();
    this.applyScheduleDisabled();
    this.opMode.setMode('update', 'Políticas');
  }

  /** Discard pending changes and return to read mode. */
  cancelEditing(): void {
    if (!this.editing()) {
      this.opMode.reset();
      return;
    }
    if (this.baseFormValue) {
      this.policyForm.setValue(this.baseFormValue as unknown as ReturnType<typeof this.policyForm.getRawValue>);
    }
    this.editing.set(false);
    this.baseFormValue = null;
    this.policyForm.disable();
    this.opMode.reset();
  }

  /** Close the edit session after a successful save. */
  private endEditSession(): void {
    this.editing.set(false);
    this.baseFormValue = null;
    this.policyForm.disable();
    this.opMode.reset();
  }

  /** Check-in/check-out are hotel-global; lock them while scoped to a room type. */
  private applyScheduleDisabled(): void {
    const locked = !!this.selectedRoomTypeId();
    const checkIn = this.policyForm.controls.checkInTime;
    const checkOut = this.policyForm.controls.checkOutTime;
    const earlyEnabled = this.policyForm.controls.earlyCheckInEnabled;
    const earlyCourtesy = this.policyForm.controls.earlyCheckInCourtesyMinutes;
    const earlyFee = this.policyForm.controls.earlyCheckInDefaultFee;
    const lateEnabled = this.policyForm.controls.lateCheckoutEnabled;
    const lateCourtesy = this.policyForm.controls.lateCheckoutCourtesyMinutes;
    const lateFee = this.policyForm.controls.lateCheckoutDefaultFee;
    const guaranteed = this.policyForm.controls.guaranteedReservation;
    const lateCutoff = this.policyForm.controls.lateArrivalCutoff;
    const noShowExec = this.policyForm.controls.noShowExecution;
    if (locked) {
      checkIn.disable();
      checkOut.disable();
      earlyEnabled.disable();
      earlyCourtesy.disable();
      earlyFee.disable();
      lateEnabled.disable();
      lateCourtesy.disable();
      lateFee.disable();
      guaranteed.disable();
      lateCutoff.disable();
      noShowExec.disable();
    } else {
      checkIn.enable();
      checkOut.enable();
      earlyEnabled.enable();
      earlyCourtesy.enable();
      earlyFee.enable();
      lateEnabled.enable();
      lateCourtesy.enable();
      lateFee.enable();
      guaranteed.enable();
      lateCutoff.enable();
      noShowExec.enable();
    }
  }

  readonly policyForm = this.formBuilder.nonNullable.group({
    checkInTime: [''],
    checkOutTime: [''],
    earlyCheckInEnabled: [true],
    earlyCheckInCourtesyMinutes: [60, [Validators.min(0), Validators.max(240)]],
    earlyCheckInDefaultFee: [0, [Validators.min(0)]],
    lateCheckoutEnabled: [true],
    lateCheckoutCourtesyMinutes: [60, [Validators.min(0), Validators.max(240)]],
    lateCheckoutDefaultFee: [0, [Validators.min(0)]],
    guaranteedReservation: [false],
    lateArrivalCutoff: ['23:59'],
    noShowExecution: ['next_day'],
    cancellationPolicy: [''],
    cancellationHours: [0, [Validators.min(0), Validators.max(720)]],
    cancellationPenaltyPercent: [100, [Validators.min(0), Validators.max(100)]],
    petsAllowed: [false],
    petFee: [0, [Validators.min(0)]],
    childrenAllowed: [false],
    extraBedFee: [0, [Validators.min(0)]],
    minStay: [1, [Validators.min(1)]],
    maxStay: [30, [Validators.min(1)]],
    childrenPolicy: [''],
    extraBedPolicy: [''],
    paymentPolicy: [''],
    petPolicy: [''],
    houseRules: [''],
  });

  constructor() {
    // Load operational stats KPI
    this.kpiApi.getOperationalStats().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (stats) => { this.opStats.set(stats); this.opStatsState.set('success'); },
      error: () => this.opStatsState.set('error'),
    });

    // Load occupancy trend (for line chart)
    this.kpiApi.getOccupancyTrend(14).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (trend) => this.occupancyTrend.set(trend),
      error: () => this.occupancyTrend.set(null),
    });

    // Carga por query param (navegación manual con prop_id en URL)
    this.route.queryParamMap
      .pipe(
        map((params) => Number(params.get('prop_id') ?? '0')),
        distinctUntilChanged(),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((propId) => {
        this.selectedPropId.set(propId);
        this.selectedRoomTypeId.set('');
      });

    // Auto-carga en modo single-hotel: cuando el contexto esté ready,
    // cargar automáticamente sin esperar navegación
    effect(() => {
      if (this.propertyCtx.ready() && this.propertyCtx.singleHotelMode()) {
        const propId = this.propertyCtx.currentPropId();
        if (propId && this.selectedPropId() !== propId) {
          this.selectedPropId.set(propId);
          this.selectedRoomTypeId.set('');
          this.selectedRatePlanId.set('');
        }
      }
    });

    // Apply side effects when fresh policies arrive
    effect(() => {
      const err = this.policiesResource.error();
      const msg = (err as unknown as ApiError)?.message;
      if (msg) this.toast.error(msg);
    });

    effect(() => {
      const vm = this.policiesResource.value();
      if (!vm || this.editing() || vm === this.lastAppliedVm) return;
      this.lastAppliedVm = vm;
      this.propertyCtx.setProperty(vm.propId, vm.hotelName);

      // Save hotel-level check-in/check-out (always take first non-empty value)
      if (!vm.roomTypeId || !this.hotelCheckInTime) {
        this.hotelCheckInTime = vm.checkInTime;
        this.hotelCheckOutTime = vm.checkOutTime;
      }

      this.policyForm.setValue({
        // Check-in/check-out: always use hotel-level values (global, not per-room)
        checkInTime: this.hotelCheckInTime || vm.checkInTime,
        checkOutTime: this.hotelCheckOutTime || vm.checkOutTime,
        earlyCheckInEnabled: vm.earlyCheckInEnabled,
        earlyCheckInCourtesyMinutes: vm.earlyCheckInCourtesyMinutes,
        earlyCheckInDefaultFee: vm.earlyCheckInDefaultFee,
        lateCheckoutEnabled: vm.lateCheckoutEnabled,
        lateCheckoutCourtesyMinutes: vm.lateCheckoutCourtesyMinutes,
        lateCheckoutDefaultFee: vm.lateCheckoutDefaultFee,
        guaranteedReservation: vm.guaranteedReservation,
        lateArrivalCutoff: vm.lateArrivalCutoff,
        noShowExecution: vm.noShowExecution,
        cancellationPolicy: vm.cancellationPolicy,
        cancellationHours: vm.cancellationHours,
        cancellationPenaltyPercent: vm.cancellationPenaltyPercent,
        petsAllowed: vm.petsAllowed,
        petFee: vm.petFee,
        childrenAllowed: vm.childrenAllowed,
        extraBedFee: vm.extraBedFee,
        minStay: vm.minStay,
        maxStay: vm.maxStay,
        childrenPolicy: vm.childrenPolicy,
        extraBedPolicy: vm.extraBedPolicy,
        paymentPolicy: vm.paymentPolicy,
        petPolicy: vm.petPolicy,
        houseRules: vm.houseRules,
      });
    });

    // Read-only by default: the form only becomes editable inside an explicit
    // edit session (mode-aware UI). setValue keeps working while disabled, so
    // the httpResource effect above still populates fresh values.
    this.policyForm.disable();
    this.destroyRef.onDestroy(() => this.opMode.reset());
  }

  onPropSelected(event: { propId: number; label: string }) {
    // Changing the property reloads a different policy set — leave any edit session.
    this.cancelEditing();
    if (!event.propId) this.propertyCtx.clear();
    else this.propertyCtx.setProperty(event.propId, event.label || `Propiedad #${event.propId}`);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null },
    });
  }

  switchRoomType(roomTypeId: string) {
    if (roomTypeId === this.selectedRoomTypeId()) return;
    this.cancelEditing();
    this.selectedRoomTypeId.set(roomTypeId);
    // Clear rate plan when switching room type (mutually exclusive scoping)
    if (roomTypeId) this.selectedRatePlanId.set('');
  }

  switchRatePlan(ratePlanId: string) {
    if (ratePlanId === this.selectedRatePlanId()) return;
    this.cancelEditing();
    this.selectedRatePlanId.set(ratePlanId);
    // Clear room type when switching rate plan (mutually exclusive scoping)
    if (ratePlanId) this.selectedRoomTypeId.set('');
  }

  savePolicies() {
    const current = this.policiesResource.value();
    if (!current || this.policyForm.invalid) {
      this.policyForm.markAllAsTouched();
      return;
    }
    const raw = this.policyForm.getRawValue();

    // Update hotel-level check-in/check-out whenever saved (regardless of room type)
    this.hotelCheckInTime = raw.checkInTime;
    this.hotelCheckOutTime = raw.checkOutTime;

    const rtId = this.selectedRoomTypeId();

    const payload = mapPoliciesPayload({
      ...current,
      // Check-in/check-out: only send if saving hotel-wide (no room type selected),
      // because these are global hotel settings, not per-room-type
      checkInTime: rtId ? '' : raw.checkInTime,
      checkOutTime: rtId ? '' : raw.checkOutTime,
      earlyCheckInEnabled: raw.earlyCheckInEnabled,
      earlyCheckInCourtesyMinutes: raw.earlyCheckInCourtesyMinutes,
      earlyCheckInDefaultFee: raw.earlyCheckInDefaultFee,
      lateCheckoutEnabled: raw.lateCheckoutEnabled,
      lateCheckoutCourtesyMinutes: raw.lateCheckoutCourtesyMinutes,
      lateCheckoutDefaultFee: raw.lateCheckoutDefaultFee,
      guaranteedReservation: raw.guaranteedReservation,
      lateArrivalCutoff: raw.lateArrivalCutoff,
      noShowExecution: raw.noShowExecution as PoliciesViewModel['noShowExecution'],
      cancellationPolicy: raw.cancellationPolicy,
      cancellationHours: raw.cancellationHours,
      cancellationPenaltyPercent: raw.cancellationPenaltyPercent,
      petsAllowed: raw.petsAllowed,
      petFee: raw.petFee,
      childrenAllowed: raw.childrenAllowed,
      extraBedFee: raw.extraBedFee,
      minStay: raw.minStay,
      maxStay: raw.maxStay,
      childrenPolicy: raw.childrenPolicy,
      extraBedPolicy: raw.extraBedPolicy,
      paymentPolicy: raw.paymentPolicy,
      petPolicy: raw.petPolicy,
      houseRules: raw.houseRules,
      roomTypeId: rtId,
      ratePlanId: this.selectedRatePlanId(),
    });
    this.api
      .savePolicies(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.endEditSession();
          this.policiesResource.reload();
          this.toast.success('Políticas actualizadas');
        },
        error: (error: ApiError) => {
          this.toast.error(error.message || 'No fue posible guardar las políticas.');
        },
      });
  }

  /** Chart data for occupancy trend — only show when no hotel selected */
  readonly occupancyChartData = computed(() => {
    const trend = this.occupancyTrend();
    if (!trend || this.selectedPropId() > 0) return null;
    return {
      labels: trend.dates.map((d) => {
        const [, m, day] = d.split('-');
        return `${day}/${m}`;
      }),
      datasets: [
        { label: 'Check-ins', data: trend.check_ins, color: '#2563eb' },
        { label: 'Check-outs', data: trend.check_outs, color: '#d97706' },
      ],
    };
  });
}
