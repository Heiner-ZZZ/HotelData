import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { RateCalendarTableComponent } from '../../components/rate-calendar-table/rate-calendar-table';
import { RatePlanTableComponent } from '../../components/rate-plan-table/rate-plan-table';
import type { RatesPageViewModel } from '../../models/rates.model';
import { RatesApiService } from '../../services/rates-api.service';

@Component({
  selector: 'app-rates-page',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    RatePlanTableComponent,
    RateCalendarTableComponent
  ],
  templateUrl: './rates-page.html',
  styleUrl: './rates-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RatesPageComponent {
  private readonly api = inject(RatesApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<RatesPageViewModel | null>(null);
  readonly feedback = signal<string>('');
  readonly errorMessage = signal<string>('');

  readonly filterForm = this.fb.nonNullable.group({
    propId: 0
  });

  readonly createPlanForm = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    description: [''],
    baseRate: [0, [Validators.required, Validators.min(0)]],
    currency: ['USD', [Validators.required]],
    isActive: [true]
  });

  readonly createCalendarForm = this.fb.nonNullable.group({
    ratePlanId: ['', [Validators.required]],
    date: ['', [Validators.required]],
    rateAmount: [0, [Validators.required, Validators.min(0)]],
    minStayNights: [1, [Validators.required, Validators.min(1)]],
    isClosed: [false]
  });

  constructor() {
    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const propId = Number(params.get('propId') ?? '0') || 0;
      this.load(propId);
    });
  }

  selectProperty() {
    const propId = this.filterForm.getRawValue().propId;
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { propId: propId || null }
    });
  }

  submitPlan() {
    const vm = this.viewModel();
    if (!vm || this.createPlanForm.invalid) {
      this.createPlanForm.markAllAsTouched();
      return;
    }

    this.feedback.set('');
    this.errorMessage.set('');
    this.api
      .createRatePlan(vm.property.propId, this.createPlanForm.getRawValue())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.feedback.set('Plan tarifario registrado.');
          this.createPlanForm.patchValue({
            name: '',
            description: '',
            baseRate: 0,
            currency: 'USD',
            isActive: true
          });
          this.load(vm.property.propId);
        },
        error: (error) => {
          this.errorMessage.set(error?.error?.detail || 'No fue posible guardar el plan tarifario.');
        }
      });
  }

  submitCalendar() {
    const vm = this.viewModel();
    if (!vm || this.createCalendarForm.invalid) {
      this.createCalendarForm.markAllAsTouched();
      return;
    }

    this.feedback.set('');
    this.errorMessage.set('');
    this.api
      .createRateCalendarRow(vm.property.propId, this.createCalendarForm.getRawValue())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.feedback.set('Tarifa por fecha actualizada.');
          this.createCalendarForm.patchValue({
            rateAmount: 0,
            minStayNights: 1,
            isClosed: false
          });
          this.load(vm.property.propId);
        },
        error: (error) => {
          this.errorMessage.set(error?.error?.detail || 'No fue posible guardar la tarifa por fecha.');
        }
      });
  }

  private load(initialPropId: number) {
    this.viewState.set('loading');
    this.feedback.set('');
    this.errorMessage.set('');
    this.api
      .getRates(initialPropId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (vm) => {
          this.viewModel.set(vm);
          this.filterForm.patchValue({ propId: vm.property.propId }, { emitEvent: false });
          const currentRatePlanId =
            this.createCalendarForm.getRawValue().ratePlanId || vm.options.ratePlans[0]?.ratePlanId || '';
          this.createCalendarForm.patchValue({ ratePlanId: currentRatePlanId }, { emitEvent: false });
          this.viewState.set(vm.ratePlans.length || vm.calendar.length ? 'success' : 'empty');
        },
        error: () => {
          this.viewState.set('error');
        }
      });
  }
}
