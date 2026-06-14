import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, of, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { mapPoliciesPayload } from '../../mappers/policies.mapper';
import type { PoliciesViewModel } from '../../models/policies.model';
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
    PropertySelectorComponent,
    ReactiveFormsModule,
  ],
  templateUrl: './policies-page.html',
  styleUrl: './policies-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PoliciesPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(PoliciesApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<PoliciesViewModel | null>(null);
  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly selectedPropId = signal(0);
  readonly selectedLabel = signal('');

  readonly policyForm = this.formBuilder.nonNullable.group({
    checkInTime: ['', [Validators.required]],
    checkOutTime: ['', [Validators.required]],
    cancellationPolicy: ['', [Validators.required]],
    childrenPolicy: [''],
    extraBedPolicy: [''],
    paymentPolicy: [''],
    petPolicy: [''],
    houseRules: [''],
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
          return propId > 0 ? this.api.getPolicies(propId) : of(null);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (policies) => {
          if (policies) {
            this.viewModel.set(policies);
            this.selectedPropId.set(policies.propId);
            this.selectedLabel.set(policies.hotelName);
            this.policyForm.setValue({
              checkInTime: policies.checkInTime,
              checkOutTime: policies.checkOutTime,
              cancellationPolicy: policies.cancellationPolicy,
              childrenPolicy: policies.childrenPolicy,
              extraBedPolicy: policies.extraBedPolicy,
              paymentPolicy: policies.paymentPolicy,
              petPolicy: policies.petPolicy,
              houseRules: policies.houseRules,
            });
            this.viewState.set('success');
          } else {
            this.viewModel.set(null);
            this.viewState.set('empty');
          }
        },
        error: () => this.viewState.set('error'),
      });
  }

  onPropSelected(propId: number) {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: propId || null },
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
      houseRules: raw.houseRules,
    });
    this.api
      .savePolicies(payload)
      .pipe(
        switchMap(() => this.api.getPolicies(current.propId)),
        takeUntilDestroyed(this.destroyRef),
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
        },
      });
  }
}
