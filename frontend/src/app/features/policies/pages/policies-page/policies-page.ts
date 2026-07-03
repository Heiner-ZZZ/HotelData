import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, of, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { KpiChartComponent } from '../../../../shared/ui/kpi-chart/kpi-chart';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { mapPoliciesPayload } from '../../mappers/policies.mapper';
import type { PoliciesViewModel, PolicyRoomTypeOption } from '../../models/policies.model';
import { PoliciesApiService } from '../../services/policies-api.service';
import { KpiApiService, type OccupancyTrendResponse, type OperationalStatsResponse } from '../../../../shared/services/kpi-api.service';
import { PolicySummaryCardsComponent } from '../../components/policy-summary-cards/policy-summary-cards';
import { AiSuggestDirective } from '../../../../core/directives/ai-suggest.directive';

@Component({
  selector: 'app-policies-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    KpiChartComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    PolicySummaryCardsComponent,
    PropertySelectorComponent,
    ReactiveFormsModule,
    AiSuggestDirective,
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
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  readonly propertyCtx = inject(PropertyContextService);

  // ── KPI: Operational stats ──
  readonly opStats = signal<OperationalStatsResponse | null>(null);
  readonly opStatsState = signal<'loading' | 'success' | 'error'>('loading');

  // ── KPI: Occupancy trend (line chart, hidden when hotel selected) ──
  readonly occupancyTrend = signal<OccupancyTrendResponse | null>(null);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<PoliciesViewModel | null>(null);
  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly selectedPropId = signal(0);
  readonly selectedLabel = signal('');

  readonly selectedRoomTypeId = signal('');
  readonly roomTypeOptions = signal<PolicyRoomTypeOption[]>([]);

  /** Hotel-level check-in/check-out — never overridden by room-type policies. */
  private hotelCheckInTime = '';
  private hotelCheckOutTime = '';

  readonly policyForm = this.formBuilder.nonNullable.group({
    checkInTime: [''],
    checkOutTime: [''],
    cancellationPolicy: [''],
    cancellationHours: [0, [Validators.min(0), Validators.max(720)]],
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
    roomTypeId: [''],
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
      error: () => {},
    });

    // Carga por query param (navegación manual con prop_id en URL)
    this.route.queryParamMap
      .pipe(
        map((params) => Number(params.get('prop_id') ?? '0')),
        distinctUntilChanged(),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((propId) => this.loadPolicies(propId));

    // Auto-carga en modo single-hotel: cuando el contexto esté ready,
    // cargar automáticamente sin esperar navegación
    effect(() => {
      if (this.propertyCtx.ready() && this.propertyCtx.singleHotelMode()) {
        const propId = this.propertyCtx.currentPropId();
        if (propId && this.selectedPropId() !== propId) {
          this.loadPolicies(propId);
        }
      }
    });
  }

  private loadPolicies(propId: number) {
    this.viewState.set('loading');
    this.message.set('');
    this.errorMessage.set('');
    this.selectedRoomTypeId.set('');

    if (propId > 0) {
      this.api.getPolicies(propId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (policies) => this.onPoliciesLoaded(policies),
        error: () => this.viewState.set('error'),
      });
    } else {
      this.onPoliciesLoaded(null);
    }
  }

  private onPoliciesLoaded(policies: PoliciesViewModel | null) {
    if (policies) {
      this.viewModel.set(policies);
      this.selectedPropId.set(policies.propId);
      this.selectedLabel.set(policies.hotelName);
      this.roomTypeOptions.set(policies.roomTypes);
      this.selectedRoomTypeId.set(policies.roomTypeId);
      this.propertyCtx.setProperty(policies.propId, policies.hotelName);

      // Save hotel-level check-in/check-out (always take first non-empty value)
      if (!policies.roomTypeId || !this.hotelCheckInTime) {
        this.hotelCheckInTime = policies.checkInTime;
        this.hotelCheckOutTime = policies.checkOutTime;
      }

      this.policyForm.setValue({
        // Check-in/check-out: always use hotel-level values (global, not per-room)
        checkInTime: this.hotelCheckInTime || policies.checkInTime,
        checkOutTime: this.hotelCheckOutTime || policies.checkOutTime,
        cancellationPolicy: policies.cancellationPolicy,
        cancellationHours: policies.cancellationHours,
        petsAllowed: policies.petsAllowed,
        petFee: policies.petFee,
        childrenAllowed: policies.childrenAllowed,
        extraBedFee: policies.extraBedFee,
        minStay: policies.minStay,
        maxStay: policies.maxStay,
        childrenPolicy: policies.childrenPolicy,
        extraBedPolicy: policies.extraBedPolicy,
        paymentPolicy: policies.paymentPolicy,
        petPolicy: policies.petPolicy,
        houseRules: policies.houseRules,
        roomTypeId: policies.roomTypeId,
      });
      this.viewState.set('success');
    } else {
      this.viewModel.set(null);
      this.viewState.set('empty');
      this.propertyCtx.clear();
    }
  }

  onPropSelected(event: { propId: number; label: string }) {
    if (!event.propId) this.propertyCtx.clear();
    else this.propertyCtx.setProperty(event.propId, event.label || `Propiedad #${event.propId}`);
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null },
    });
  }

  switchRoomType(roomTypeId: string) {
    if (roomTypeId === this.selectedRoomTypeId()) return;
    const propId = this.selectedPropId();
    if (!propId) return;

    this.viewState.set('loading');
    this.message.set('');
    this.errorMessage.set('');

    const obs = roomTypeId
      ? this.api.getPolicies(propId, roomTypeId)
      : this.api.getPolicies(propId);

    obs.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (policies) => this.onPoliciesLoaded(policies),
      error: () => this.viewState.set('error'),
    });
  }

  savePolicies() {
    const current = this.viewModel();
    if (!current || this.policyForm.invalid) {
      this.policyForm.markAllAsTouched();
      return;
    }
    const raw = this.policyForm.getRawValue();

    // Update hotel-level check-in/check-out whenever saved (regardless of room type)
    this.hotelCheckInTime = raw.checkInTime;
    this.hotelCheckOutTime = raw.checkOutTime;

    const propId = current.propId;
    const rtId = this.selectedRoomTypeId();

    const payload = mapPoliciesPayload({
      ...current,
      checkInTime: raw.checkInTime,
      checkOutTime: raw.checkOutTime,
      cancellationPolicy: raw.cancellationPolicy,
      cancellationHours: raw.cancellationHours,
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
    });
    this.api
      .savePolicies(payload)
      .pipe(
        switchMap(() => {
          return rtId ? this.api.getPolicies(propId, rtId) : this.api.getPolicies(propId);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (policies) => {
          this.onPoliciesLoaded(policies);
          this.message.set('Políticas actualizadas');
          this.errorMessage.set('');
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible guardar las políticas.');
          this.message.set('');
        },
      });
  }

  /** Chart data for occupancy trend — only show when no hotel selected */
  readonly occupancyChartData = computed(() => {
    const trend = this.occupancyTrend();
    if (!trend || this.selectedPropId() > 0) return null;
    return {
      labels: trend.dates.map((d) => {
        const [y, m, day] = d.split('-');
        return `${day}/${m}`;
      }),
      datasets: [
        { label: 'Check-ins', data: trend.check_ins, color: '#2563eb' },
        { label: 'Check-outs', data: trend.check_outs, color: '#d97706' },
      ],
    };
  });
}
