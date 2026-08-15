import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, input, output, signal } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { forkJoin, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import {
  parseCouponConflict,
  type CouponConflict,
} from '../../../../shared/utils/coupon-conflict.util';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { RatesApiService } from '../../services/rates-api.service';
import type { RatesViewModel } from '../../models/rates.model';

export interface PromoEditState {
  campaignId: string;
  name: string;
  description: string;
  discountPercent: number;
  couponCount: number;
  /** Cupones ya utilizados en reservas — no se pueden retirar ni reducir por debajo. */
  couponUsed: number;
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
  private readonly confirmDialog = inject(ConfirmDialogService);

  readonly viewModel = input<RatesViewModel | null>(null);
  /** Pass a promo to edit — component auto-loads it into the form. */
  readonly editingPromo = input<PromoEditState | null>(null);
  readonly promoCreated = output<void>();
  /** El usuario canceló la edición en curso — la página debe limpiar editingPromo. */
  readonly cancelEditChange = output<void>();
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

  /** Error del backend (o bloqueo client-side) mostrado inline en el form. */
  readonly inlineError = signal<string | null>(null);

  /** Conflicto de código ESTRUCTURADO (400 ``COUPON_CODE_EXISTS``): el código
   *  ya pertenece a la campaña «X». Banner destacado que reemplaza el inline
   *  genérico — muestra la campaña dueña y ofrece quitar el código. */
  readonly couponConflict = signal<CouponConflict | null>(null);

  /** Snapshot reactivo del form para derivar la advertencia de reducción. */
  private readonly formValues = toSignal(this.form.valueChanges, {
    initialValue: this.form.getRawValue(),
  });

  /**
   * Cupones sin usar que se RETIRARÁN (borrado lógico, con trazabilidad) si
   * se guarda con el couponCount actual: original de la campaña − valor del
   * form, solo cuando es positivo y estamos en modo edición. null = sin aviso.
   */
  readonly couponsToRetire = computed<number | null>(() => {
    const promo = this.editing();
    if (!promo) return null;
    const current = Number(this.formValues()?.couponCount ?? promo.couponCount);
    const diff = promo.couponCount - current;
    return diff > 0 ? diff : null;
  });

  /**
   * Bloqueo DURO: si la campaña tiene cupones ya usados, NINGUNA edición se
   * puede guardar — el backend (Guard 2) rechaza cualquier cambio con cupones
   * utilizados. El aviso proactivo 'N cupones usados: desactiva y crea una
   * nueva' reemplaza el error del backend al guardar. Devuelve el nº de usados
   * (null = sin bloqueo). Tiene prioridad sobre couponsToRetire en el template.
   */
  readonly usedCouponsBlock = computed<number | null>(() => {
    const promo = this.editing();
    if (!promo) return null;
    return promo.couponUsed > 0 ? promo.couponUsed : null;
  });

  readonly isEditing = computed(() => this.editing() !== null);

  /**
   * ¿Hay cambios sin guardar respecto a la promo cargada? Compara el snapshot
   * del form contra los valores originales (editar y revertir no cuenta). El
   * couponCode no se envía en updatePromotion, así que no se compara. Se usa
   * para pedir confirmación antes de cancelar la edición.
   */
  readonly hasUnsavedChanges = computed<boolean>(() => {
    const promo = this.editing();
    if (!promo) return false;
    const v = this.formValues();
    return v.name !== promo.name
      || v.description !== promo.description
      || v.discountPercent !== promo.discountPercent
      || v.couponCount !== promo.couponCount
      || v.startDate !== promo.startDate
      || v.endDate !== promo.endDate
      || v.isActive !== promo.isActive;
  });

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

    // Editar el código de cupón invalida el conflicto al instante (el usuario
    // ya cambió de idea — el banner no debe quedarse colgado de un código viejo).
    this.form.controls.couponCode.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.couponConflict.set(null));
  }

  async cancelEdit(): Promise<void> {
    if (!this.editing()) return;
    // Con cambios sin guardar se pide confirmación antes de descartarlos.
    if (this.hasUnsavedChanges()) {
      const ok = await this.confirmDialog.open({
        title: 'Descartar cambios',
        message: 'Tienes cambios sin guardar en esta promoción. ¿Quieres descartarlos?',
        confirmLabel: 'Descartar cambios',
        cancelLabel: 'Seguir editando',
        variant: 'warning',
      });
      if (!ok) return;
    }
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
    // La página limpia editingPromo → el mode-indicator vuelve a insert/read.
    this.cancelEditChange.emit();
  }

  submit(): void {
    const vm = this.viewModel();
    if (!vm || this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const value = this.form.getRawValue();

    // Bloqueo client-side: una campaña con cupones usados no se puede editar.
    // El aviso proactivo del template ('N cupones usados: desactiva y crea una
    // nueva') lo explica, sin round-trip al backend.
    if (this.usedCouponsBlock() !== null) {
      return;
    }
    this.inlineError.set(null);
    this.couponConflict.set(null);

    // Cupones retirados (borrado lógico) en ESTE guardado: lo reporta la
    // respuesta del backend al reducir coupon_count y se muestra en el toast.
    let retiredCoupons = 0;

    const obs = this.isEditing()
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
        switchMap((result) => {
          retiredCoupons = Math.max(0, Number((result as { coupons_retired?: number } | null)?.coupons_retired ?? 0));
          return forkJoin({
            rates: this.api.getRates(vm.propId),
            plans: this.api.getRatePlanOptions(vm.propId),
            promotions: this.api.listPropertyPromotions(vm.propId),
          });
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: () => {
          const baseMessage = this.isEditing() ? 'Promoción actualizada' : 'Promoción creada';
          const retiredLabel = retiredCoupons === 1 ? '1 cupón retirado' : `${retiredCoupons} cupones retirados`;
          this.messageChange.emit(retiredCoupons > 0 ? `${baseMessage} · ${retiredLabel}` : baseMessage);
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
          const conflict = parseCouponConflict(error);
          if (conflict) {
            // Banner destacado y accionable — reemplaza el inline genérico y
            // NO dispara el toast del padre (el interceptor global ya avisa).
            this.couponConflict.set(conflict);
            this.inlineError.set(null);
            return;
          }
          const message = error.message || 'No fue posible crear la promoción.';
          // El error del backend se muestra inline en el form (además del toast).
          this.inlineError.set(message);
          this.errorChange.emit(message);
          this.messageChange.emit('');
        },
      });
  }

  /** «Usar otro código» desde el banner: limpia el campo de cupón (el cupón
   *  es opcional en Tarifas — crear la campaña sin él también resuelve). */
  clearConflictCode(): void {
    this.form.controls.couponCode.setValue('');
    this.couponConflict.set(null);
  }

  /** Descarta el aviso (el conflicto reaparece si se reintenta con el mismo
   *  código — el backend es la autoridad). */
  dismissCouponConflict(): void {
    this.couponConflict.set(null);
  }
}
