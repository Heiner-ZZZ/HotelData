import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, forkJoin, map, of, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { mapPoliciesPayload } from '../../mappers/policies.mapper';
import type { PoliciesViewModel, PolicyPropertyOption } from '../../models/policies.model';
import { PoliciesApiService } from '../../services/policies-api.service';
import { PolicySummaryCardsComponent } from '../../components/policy-summary-cards/policy-summary-cards';

@Component({
  selector: 'app-policies-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    PolicySummaryCardsComponent,
    ReactiveFormsModule
  ],
  templateUrl: './policies-page.html',
  styleUrl: './policies-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PoliciesPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(PoliciesApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<PoliciesViewModel | null>(null);
  readonly propertyOptions = signal<PolicyPropertyOption[]>([]);
  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly selectorForm = this.formBuilder.nonNullable.group({
    propId: [0, [Validators.required, Validators.min(1)]]
  });

  readonly policyForm = this.formBuilder.nonNullable.group({
    checkInTime: ['', [Validators.required]],
    checkOutTime: ['', [Validators.required]],
    cancellationPolicy: ['', [Validators.required]],
    childrenPolicy: [''],
    extraBedPolicy: [''],
    paymentPolicy: [''],
    petPolicy: [''],
    houseRules: ['']
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
          return forkJoin({
            options: this.api.getOptions(),
            policies: propId > 0 ? this.api.getPolicies(propId) : of(null)
          });
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: ({ options, policies }) => {
          this.propertyOptions.set(options);
          if (!this.selectorForm.controls.propId.value && options.length) {
            this.selectorForm.controls.propId.setValue(options[0].propId);
          }
          if (policies) {
            this.viewModel.set(policies);
            this.selectorForm.controls.propId.setValue(policies.propId, { emitEvent: false });
            this.policyForm.setValue({
              checkInTime: policies.checkInTime,
              checkOutTime: policies.checkOutTime,
              cancellationPolicy: policies.cancellationPolicy,
              childrenPolicy: policies.childrenPolicy,
              extraBedPolicy: policies.extraBedPolicy,
              paymentPolicy: policies.paymentPolicy,
              petPolicy: policies.petPolicy,
              houseRules: policies.houseRules
            });
            this.viewState.set('success');
          } else {
            this.viewModel.set(null);
            this.viewState.set(options.length ? 'empty' : 'success');
          }
        },
        error: () => this.viewState.set('error')
      });
  }

  selectProperty() {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: this.selectorForm.controls.propId.value || null }
    });
  }

  savePolicies() {
    const current = this.viewModel();
    if (!current || this.policyForm.invalid) {
      this.policyForm.markAllAsTouched();
      return;
    }
    const raw = this.policyForm.getRawValue();
    const payload = mapPoliciesPayload({
      ...current,
      checkInTime: raw.checkInTime,
      checkOutTime: raw.checkOutTime,
      cancellationPolicy: raw.cancellationPolicy,
      childrenPolicy: raw.childrenPolicy,
      extraBedPolicy: raw.extraBedPolicy,
      paymentPolicy: raw.paymentPolicy,
      petPolicy: raw.petPolicy,
      houseRules: raw.houseRules
    });
    this.api
      .savePolicies(payload)
      .pipe(
        switchMap(() => this.api.getPolicies(current.propId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (policies) => {
          this.viewModel.set(policies);
          this.message.set('Politicas actualizadas');
          this.errorMessage.set('');
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible guardar las politicas.');
          this.message.set('');
        }
      });
  }
}
