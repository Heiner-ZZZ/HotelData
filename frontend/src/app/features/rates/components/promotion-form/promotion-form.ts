import { ChangeDetectionStrategy, Component, DestroyRef, effect, inject, input, output, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { forkJoin, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { RatesApiService } from '../../services/rates-api.service';
import type { RatesViewModel } from '../../models/rates.model';

export interface PromoEditState {
  campaignId: string;
  name: string;
  description: string;
  discountPercent: number;
  couponCount: number;
  startDate: string;
  endDate: string;
  isActive: boolean;
}

@Component({
  selector: 'app-promotion-form',
  imports: [ReactiveFormsModule],
  templateUrl: './promotion-form.html',
  styleUrl: './promotion-form.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PromotionFormComponent {
  private readonly api = inject(RatesApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);

  readonly viewModel = input<RatesViewModel | null>(null);
  /** Pass a promo to edit — component auto-loads it into the form. */
  readonly editingPromo = input<PromoEditState | null>(null);
  readonly promoCreated = output<void>();
  readonly errorChange = output<string>();
  readonly messageChange = output<string>();

  readonly form = this.formBuilder.nonNullable.group({
    name: ['', [Validators.required]],
    description: [''],
    discountPercent: [10, [Validators.required, Validators.min(1), Validators.max(100)]],
    couponCount: [10, [Validators.required, Validators.min(1), Validators.max(1000)]],
    startDate: ['', [Validators.required]],
    endDate: ['', [Validators.required]],
    couponCode: [''],
    isActive: [true],
  });

  readonly editing = signal<PromoEditState | null>(null);

  get isEditing(): boolean {
    return this.editing() !== null;
  }

  constructor() {
    // React to editingPromo input changes — auto-load form for editing
    effect(() => {
      const promo = this.editingPromo();
      if (promo) {
        this.editing.set(promo);
        this.form.patchValue({
          name: promo.name,
          description: promo.description,
          discountPercent: promo.discountPercent,
          couponCount: promo.couponCount,
          startDate: promo.startDate,
          endDate: promo.endDate,
          isActive: promo.isActive,
        });
      }
    });
  }

  cancelEdit(): void {
    this.editing.set(null);
    this.form.reset({
      name: '',
      description: '',
      discountPercent: 10,
      couponCount: 10,
      startDate: '',
      endDate: '',
      couponCode: '',
      isActive: true,
    });
  }

  submit(): void {
    const vm = this.viewModel();
    if (!vm || this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const value = this.form.getRawValue();

    const obs = this.isEditing
      ? this.api.updatePromotion(this.editing()!.campaignId, {
          name: value.name,
          description: value.description,
          discountPercent: value.discountPercent,
          couponCount: value.couponCount,
          startDate: value.startDate,
          endDate: value.endDate,
          isActive: value.isActive,
        })
      : this.api.createPromotion({
          propId: vm.propId,
          name: value.name,
          description: value.description,
          discountPercent: value.discountPercent,
          startDate: value.startDate,
          endDate: value.endDate,
          couponCount: value.couponCount,
          couponCode: value.couponCode,
          isActive: value.isActive,
        });

    obs
      .pipe(
        switchMap(() => forkJoin({
          rates: this.api.getRates(vm.propId),
          plans: this.api.getRatePlanOptions(vm.propId),
          promotions: this.api.listPropertyPromotions(vm.propId),
        })),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: () => {
          this.messageChange.emit(this.isEditing ? 'Promoción actualizada' : 'Promoción creada');
          this.errorChange.emit('');
          this.editing.set(null);
          this.form.reset({
            name: '',
            description: '',
            discountPercent: 10,
            couponCount: 10,
            startDate: '',
            endDate: '',
            couponCode: '',
            isActive: true,
          });
          this.promoCreated.emit();
        },
        error: (error: ApiError) => {
          this.errorChange.emit(error.message || 'No fue posible crear la promoción.');
          this.messageChange.emit('');
        },
      });
  }
}
