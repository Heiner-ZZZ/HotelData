import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, forkJoin, map, of, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { RatePlanOption, RatesViewModel } from '../../models/rates.model';
import { RatesApiService } from '../../services/rates-api.service';
import { RatePlanTableComponent } from '../../components/rate-plan-table/rate-plan-table';
import { RateCalendarTableComponent } from '../../components/rate-calendar-table/rate-calendar-table';

@Component({
  selector: 'app-rates-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    PropertySelectorComponent,
    ReactiveFormsModule,
    RatePlanTableComponent,
    RateCalendarTableComponent
  ],
  templateUrl: './rates-page.html',
  styleUrl: './rates-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RatesPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(RatesApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<RatesViewModel | null>(null);
  readonly ratePlanOptions = signal<RatePlanOption[]>([]);
  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly selectedPropId = signal(0);
  readonly selectedLabel = signal('');

  /* ── Forms ── */
  readonly planForm = this.formBuilder.nonNullable.group({
    name: ['', [Validators.required]],
    description: [''],
    baseRate: [0, [Validators.required, Validators.min(0)]],
    currency: ['USD', [Validators.required]],
    isActive: [true]
  });

  readonly calendarForm = this.formBuilder.nonNullable.group({
    ratePlanId: ['', [Validators.required]],
    date: ['', [Validators.required]],
    rateAmount: [0, [Validators.required, Validators.min(0)]],
    minStayNights: [1, [Validators.required, Validators.min(1)]],
    isClosed: [false]
  });

  readonly promoForm = this.formBuilder.nonNullable.group({
    name: ['', [Validators.required]],
    description: [''],
    discountPercent: [10, [Validators.required, Validators.min(0), Validators.max(100)]],
    startDate: ['', [Validators.required]],
    endDate: ['', [Validators.required]],
    couponCode: [''],
    isActive: [true]
  });

  constructor() {
    this.route.queryParamMap
      .pipe(
        map((params) => Number(params.get('prop_id') ?? '0')),
        distinctUntilChanged(),
        switchMap((propId) => {
          this.viewState.set('loading');
          this.message.set('');
          this.errorMessage.set('');
          const load = propId > 0
            ? forkJoin({
                rates: this.api.getRates(propId),
                plans: this.api.getRatePlanOptions(propId)
              })
            : of(null);
          return load;
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (result) => {
          if (result) {
            this.viewModel.set(result.rates);
            this.ratePlanOptions.set(result.plans);
            this.selectedPropId.set(result.rates.propId);
            this.selectedLabel.set(result.rates.hotelLabel);
            this.viewState.set('success');
          } else {
            this.viewModel.set(null);
            this.ratePlanOptions.set([]);
            this.viewState.set('empty');
          }
        },
        error: () => this.viewState.set('error')
      });
  }

  onPropSelected(propId: number): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: propId || null }
    });
  }

  createRatePlan() {
    const current = this.viewModel();
    if (!current || this.planForm.invalid) {
      this.planForm.markAllAsTouched();
      return;
    }

    const value = this.planForm.getRawValue();
    this.api
      .createRatePlan({
        propId: current.propId,
        name: value.name,
        description: value.description,
        baseRate: value.baseRate,
        currency: value.currency,
        isActive: value.isActive
      })
      .pipe(
        switchMap(() =>
          forkJoin({
            rates: this.api.getRates(current.propId),
            plans: this.api.getRatePlanOptions(current.propId)
          })
        ),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: ({ rates, plans }) => {
          this.viewModel.set(rates);
          this.ratePlanOptions.set(plans);
          this.message.set('Plan tarifario registrado');
          this.errorMessage.set('');
          this.planForm.reset({
            name: '',
            description: '',
            baseRate: 0,
            currency: 'USD',
            isActive: true
          });
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible registrar el plan tarifario.');
          this.message.set('');
        }
      });
  }

  saveRate() {
    const current = this.viewModel();
    if (!current || this.calendarForm.invalid) {
      this.calendarForm.markAllAsTouched();
      return;
    }

    const value = this.calendarForm.getRawValue();
    this.api
      .saveRate({
        propId: current.propId,
        ratePlanId: value.ratePlanId,
        date: value.date,
        rateAmount: value.rateAmount,
        minStayNights: value.minStayNights,
        isClosed: value.isClosed
      })
      .pipe(
        switchMap(() => this.api.getRates(current.propId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (rates) => {
          this.viewModel.set(rates);
          this.message.set('Tarifa actualizada');
          this.errorMessage.set('');
          this.calendarForm.reset({
            ratePlanId: '',
            date: '',
            rateAmount: 0,
            minStayNights: 1,
            isClosed: false
          });
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible actualizar la tarifa.');
          this.message.set('');
        }
      });
  }

  createPromotion() {
    const current = this.viewModel();
    if (!current || this.promoForm.invalid) {
      this.promoForm.markAllAsTouched();
      return;
    }

    const value = this.promoForm.getRawValue();
    this.api
      .createPromotion({
        propId: current.propId,
        name: value.name,
        description: value.description,
        discountPercent: value.discountPercent,
        startDate: value.startDate,
        endDate: value.endDate,
        couponCode: value.couponCode,
        isActive: value.isActive
      })
      .pipe(
        switchMap(() => forkJoin({
          rates: this.api.getRates(current.propId),
          plans: this.api.getRatePlanOptions(current.propId)
        })),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: ({ rates, plans }) => {
          this.viewModel.set(rates);
          this.ratePlanOptions.set(plans);
          this.message.set('Promoción creada');
          this.errorMessage.set('');
          this.promoForm.reset({
            name: '',
            description: '',
            discountPercent: 10,
            startDate: '',
            endDate: '',
            couponCode: '',
            isActive: true
          });
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible crear la promoción.');
          this.message.set('');
        }
      });
  }
}
