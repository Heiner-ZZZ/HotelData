import { CurrencyPipe, DatePipe, KeyValuePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal, ViewEncapsulation } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { distinctUntilChanged, map, switchMap, tap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { CheckOutsApiService, type CheckOutDetailDto } from '../../services/check-outs-api.service';
import { CoHeaderComponent } from './partials/co-header';
import { CoStepBreadcrumbComponent } from './partials/co-step-breadcrumb';
import { CoStepSummaryComponent } from './partials/co-step-summary';
import { CoStepChargesComponent } from './partials/co-step-charges';
import { CoStepSettlementComponent } from './partials/co-step-settlement';
import { CoStepInvoiceComponent } from './partials/co-step-invoice';
import { CoStepCloseComponent } from './partials/co-step-close';
import { CoCompletedViewComponent } from './partials/co-completed-view';

@Component({
  selector: 'app-check-out-detail-page',
  imports: [
    FormsModule,
    LoadingStateComponent, ErrorStateComponent, EmptyStateComponent,
    CoHeaderComponent,
    CoStepBreadcrumbComponent,
    CoStepSummaryComponent,
    CoStepChargesComponent,
    CoStepSettlementComponent,
    CoStepInvoiceComponent,
    CoStepCloseComponent,
    CoCompletedViewComponent
  ],
  templateUrl: './check-out-detail-page.html',
  styleUrl: './check-out-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
})
export class CheckOutDetailPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly api = inject(CheckOutsApiService);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<CheckOutDetailDto | null>(null);
  readonly successMessage = signal('');
  readonly errorMessage = signal('');

  // ── Step wizard ──
  readonly currentStep = signal(1);
  readonly everythingCorrect = signal<boolean | null>(null);
  readonly steps = [
    { num: 1, label: 'Resumen', icon: 'summarize' },
    { num: 2, label: 'Cargos', icon: 'add_circle' },
    { num: 3, label: 'Liquidar', icon: 'receipt_long' },
    { num: 4, label: 'Factura', icon: 'description' },
    { num: 5, label: 'Cerrar', icon: 'logout' },
  ];

  // ── Check-out fields ──
  readonly roomInspected = signal(false);
  readonly keysReturned = signal(false);
  readonly damagesFound = signal(false);
  readonly lateCheckoutFee = signal(0);
  readonly discount = signal(0);
  readonly discountReason = signal('');
  readonly paymentMethod = signal('credit_card');
  readonly paymentRef = signal('');
  readonly observations = signal('');
  readonly splitInvoice = signal(false);

  // ── Charge creation form ──
  readonly chargeFormVisible = signal(false);
  readonly chargeConcept = signal('');
  readonly chargeCategory = signal('');
  readonly chargeAmount = signal(0);
  readonly chargeQuantity = signal(1);
  readonly chargeNote = signal('');
  readonly chargeSaving = signal(false);
  readonly chargeError = signal('');

  // ── Completion ──
  readonly completing = signal(false);
  readonly completeError = signal('');

  readonly Math = Math;
  protected readonly Number = Number;
  readonly canComplete = signal(false);
  readonly checkoutDone = computed(() => this.data()?.stay_status === 'checked_out');

  // ── Computed financials ──
  readonly roomTotal = computed(() => this.data()?.total_price ?? 0);
  readonly chargesTotal = computed(() => this.data()?.charges_total ?? 0);
  readonly lateFee = computed(() => this.lateCheckoutFee());
  readonly discountVal = computed(() => this.discount());
  readonly subtotalBeforeDiscount = computed(() =>
    (this.data()?.invoice?.subtotal ?? (this.roomTotal() + this.chargesTotal())) + this.lateFee()
  );
  readonly subtotal = computed(() => Math.max(0, this.subtotalBeforeDiscount() - this.discountVal()));
  readonly taxes = computed(() => {
    const hasAdjustments = this.lateFee() > 0 || this.discountVal() > 0;
    if (!hasAdjustments && this.data()?.invoice?.taxes) return this.data()!.invoice!.taxes;
    return Math.round(this.subtotal() * 0.16 * 100) / 100;
  });
  readonly grandTotal = computed(() => this.subtotal() + this.taxes());
  readonly depositDeducted = computed(() => {
    const d = this.data();
    if (!d) return 0;
    return d.deposit_received ? Math.round(this.roomTotal() * 0.5 * 100) / 100 : 0;
  });
  readonly balanceDue = computed(() => this.grandTotal() - this.depositDeducted());
  readonly hasExistingPayments = computed(() => {
    const d = this.data();
    return (d?.invoice?.paid_at && d.invoice.status === 'paid') ? true : false;
  });
  readonly totalPaid = computed(() => {
    if (this.hasExistingPayments()) return this.grandTotal();
    return this.depositDeducted();
  });

  readonly currency = computed(() => this.data()?.currency ?? 'USD');

  // ── Category entries for partials ──
  readonly chargeCategoryEntries = computed(() => {
    const d = this.data();
    if (!d?.charges_by_category) return [];
    return Object.entries(d.charges_by_category).map(([key, items]: [string, any]) => ({
      key,
      items,
      label: this.categoryLabel(key),
      icon: this.categoryIcon(key),
      total: this.categoryTotal(key),
    }));
  });

  readonly chargeDetailEntries = computed(() => {
    const d = this.data();
    if (!d?.charges) return [];
    return d.charges.map((c: any) => ({
      ...c,
      categoryIcon: this.categoryIcon(c.category),
      categoryLabel: this.categoryLabel(c.category),
    }));
  });

  readonly paymentMethodLabel = computed(() => {
    const method = this.data()?.check_out_payment_method;
    const labels: Record<string, string> = {
      credit_card: 'Tarjeta Crédito / Débito',
      cash: 'Efectivo (Caja Principal)',
      transfer: 'Transferencia Bancaria',
      mixed: 'Pago Mixto',
    };
    return labels[method || ''] || method || '—';
  });

  // ── Category config ──
  readonly categoryLabels: Record<string, string> = {
    minibar: 'Minibar', spa: 'Spa', restaurante: 'Restaurante',
    lavanderia: 'Lavandería', parking: 'Parking', mascotas: 'Mascotas',
    room_service: 'Room Service', danos: 'Daños', late_checkout: 'Late Checkout',
    amenities: 'Amenidades', otros: 'Otros',
  };
  readonly categoryIcons: Record<string, string> = {
    minibar: 'liquor', spa: 'spa', restaurante: 'restaurant',
    lavanderia: 'local_laundry_service', parking: 'local_parking', mascotas: 'pets',
    room_service: 'room_service', danos: 'warning', late_checkout: 'schedule',
    amenities: 'business_center', otros: 'receipt',
  };
  readonly chargeCategories = [
    { value: 'minibar', label: 'Minibar', icon: 'liquor' },
    { value: 'spa', label: 'Spa', icon: 'spa' },
    { value: 'restaurante', label: 'Restaurante', icon: 'restaurant' },
    { value: 'lavanderia', label: 'Lavandería', icon: 'local_laundry_service' },
    { value: 'parking', label: 'Parking', icon: 'local_parking' },
    { value: 'mascotas', label: 'Mascotas', icon: 'pets' },
    { value: 'room_service', label: 'Room Service', icon: 'room_service' },
    { value: 'danos', label: 'Daños', icon: 'warning' },
    { value: 'late_checkout', label: 'Late Checkout', icon: 'schedule' },
    { value: 'amenities', label: 'Amenidades', icon: 'business_center' },
    { value: 'otros', label: 'Otros', icon: 'receipt' },
  ];

  constructor() {
    this.activatedRoute.paramMap
      .pipe(
        map(params => params.get('bookingId') ?? ''),
        distinctUntilChanged(),
        tap(() => this.viewState.set('loading')),
        switchMap(bookingId => this.api.getCheckOutDetail(bookingId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (detail) => {
          this.data.set(detail);
          this.roomInspected.set(detail.check_out_room_inspected || false);
          this.keysReturned.set(detail.check_out_keys_returned || false);
          this.damagesFound.set(detail.check_out_damages_found || false);
          this.lateCheckoutFee.set(detail.check_out_late_checkout_fee || 0);
          this.discount.set(detail.check_out_discount || 0);
          this.discountReason.set(detail.check_out_discount_reason || '');
          this.paymentMethod.set(detail.check_out_payment_method || 'credit_card');
          this.paymentRef.set(detail.check_out_payment_ref || '');
          this.observations.set(detail.check_out_observations || '');
          this.canComplete.set(detail.assigned_rooms.length > 0 && detail.stay_status !== 'checked_out');
          if (detail.stay_status === 'checked_out') this.currentStep.set(5);
          this.viewState.set('success');
        },
        error: (err: ApiError) => {
          this.viewState.set(err.status === 404 ? 'empty' : 'error');
        }
      });
  }

  // ── Step navigation ──
  goToStep(n: number): void { this.currentStep.set(n); }

  nextStep(): void {
    const step = this.currentStep();
    if (step === 1 && this.everythingCorrect() === true) { this.goToStep(3); return; }
    if (step < 5) this.goToStep(step + 1);
  }

  prevStep(): void {
    if (this.currentStep() > 1) this.goToStep(this.currentStep() - 1);
  }

  setCorrect(val: boolean): void {
    this.everythingCorrect.set(val);
    if (val) { this.goToStep(3); }
    else { this.goToStep(2); }
  }

  canGoNext(): boolean {
    const step = this.currentStep();
    if (step === 1) return this.everythingCorrect() !== null;
    return true;
  }

  categoryLabel(cat: string): string {
    return this.categoryLabels[cat] || cat;
  }

  categoryIcon(cat: string): string {
    return this.categoryIcons[cat] || 'receipt';
  }

  categoryTotal(cat: string): number {
    const d = this.data();
    return d?.category_totals?.[cat] ?? 0;
  }

  chargeTotal(amount: number, qty: number): number {
    return Math.round(amount * qty * 100) / 100;
  }

  // ═══ Charge creation ═══
  toggleChargeForm(): void {
    this.chargeFormVisible.update(v => !v);
    this.chargeError.set('');
    if (this.chargeFormVisible()) {
      this.chargeConcept.set('');
      this.chargeCategory.set('');
      this.chargeAmount.set(0);
      this.chargeQuantity.set(1);
      this.chargeNote.set('');
    }
  }

  addCharge(): void {
    const d = this.data();
    const concept = this.chargeConcept().trim();
    const amount = this.chargeAmount();
    const qty = this.chargeQuantity();
    if (!d || !concept || amount <= 0) {
      this.chargeError.set('Completa el concepto y el monto del cargo.');
      return;
    }
    this.chargeSaving.set(true);
    this.chargeError.set('');

    this.api.createCharge(d.booking_id, d.prop_id, concept, amount, qty, this.chargeNote(), this.chargeCategory()).subscribe({
      next: () => {
        this.chargeSaving.set(false);
        this.chargeFormVisible.set(false);
        this.api.getCheckOutDetail(d.booking_id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
          next: (updated) => this.data.set(updated),
        });
      },
      error: (err: ApiError) => {
        this.chargeSaving.set(false);
        this.chargeError.set(err.message || 'Error al crear el cargo.');
      },
    });
  }

  // ═══ Quick category charge ═══
  quickCharge(category: string, concept: string, amount: number): void {
    const d = this.data();
    if (!d) return;
    this.chargeSaving.set(true);
    this.api.createCharge(d.booking_id, d.prop_id, concept, amount, 1, '', category).subscribe({
      next: () => {
        this.chargeSaving.set(false);
        this.api.getCheckOutDetail(d.booking_id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
          next: (updated) => this.data.set(updated),
        });
      },
      error: () => { this.chargeSaving.set(false); },
    });
  }

  completeCheckOut(): void {
    const d = this.data();
    if (!d || this.completing()) return;
    this.completing.set(true);
    this.completeError.set('');

    this.api.completeCheckOutWithDetail(d.booking_id, {
      check_out_room_inspected: this.roomInspected(),
      check_out_keys_returned: this.keysReturned(),
      check_out_damages_found: this.damagesFound(),
      check_out_late_checkout_fee: this.lateCheckoutFee(),
      check_out_discount: this.discount(),
      check_out_discount_reason: this.discountReason(),
      check_out_payment_method: this.paymentMethod(),
      check_out_payment_ref: this.paymentRef(),
      check_out_observations: this.observations(),
      split_invoice: this.splitInvoice(),
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (result) => {
        this.completing.set(false);
        this.successMessage.set(`✅ Check-out completado — Folio ${d.folio || ''}`);
        this.canComplete.set(false);
        this.goToStep(5);
        this.api.getCheckOutDetail(d.booking_id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
          next: (updated) => this.data.set(updated),
        });
      },
      error: (err: ApiError) => {
        this.completing.set(false);
        this.completeError.set(err.message || 'Error al completar check-out.');
      },
    });
  }

  roomLabel(r: CheckOutDetailDto['assigned_rooms'][number] | undefined): string {
    return r?.room_label || r?.room_number || r?.hotel_room_id || '—';
  }

  nightsArray(n: number): number[] {
    return Array.from({ length: Math.max(0, n || 0) }, (_, i) => i);
  }
}
