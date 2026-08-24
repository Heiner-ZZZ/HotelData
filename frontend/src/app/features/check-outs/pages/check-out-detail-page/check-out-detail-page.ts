import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal, ViewEncapsulation } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';

import { getErrorStatus, getErrorMessage } from '../../../../shared/utils/http-error.util';
import { AuthService } from '../../../../core/auth/auth.service';
import { OperationModeService, type OperationMode } from '../../../../core/services/operation-mode.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import type { ApiError } from '../../../../core/api/api-error.model';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { NoShowService } from '../../../../shared/services/no-show.service';
import { CheckOutsApiService, type BookingCharge, type CheckOutDetailDto, type CheckOutDetailSavePayload } from '../../services/check-outs-api.service';
import { STAY_CHECKED_IN, STAY_CHECKED_OUT, STAY_NO_SHOW } from '../../../reservations/utils/reservation-status.util';
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
    RouterLink,
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
  private readonly opMode = inject(OperationModeService);
  private readonly auth = inject(AuthService);
  private readonly noShow = inject(NoShowService);
  private readonly propertyCtx = inject(PropertyContextService);

  readonly viewState = signal<ViewState>('loading');
  /**
   * Degradación elegante: httpResource.value() LANZA cuando el request falló
   * (ej. 403 check-outs.read) y todos los computeds derivados (_opMode,
   * roomTotal, grandTotal…) lo re-leerían → spam de consola en cada
   * recomputación. Con error presente devolvemos null y la vista pasa a
   * 'forbidden'/'error' sin lanzar.
   */
  readonly data = computed(() => {
    if (this.detailResource.error()) return null;
    return this.detailResource.value() ?? null;
  });
  readonly errorMessage = signal('');
  readonly successMessage = signal('');

  // ── Reactive route param → httpResource (re-fires on bookingId change) ──
  private readonly paramMap = toSignal(this.activatedRoute.paramMap, {
    initialValue: this.activatedRoute.snapshot.paramMap,
  });
  readonly bookingId = computed(() => this.paramMap().get('bookingId') ?? '');

  // prop_id reactivo: prioriza ?prop_id de la URL, fallback a PropertyContext (single-hotel).
  // Sin prop_id el backend responde 400 `Contexto de hotel requerido` (require_prop_permission).
  private readonly queryParamMap = toSignal(
    ((this.activatedRoute.queryParamMap ?? this.activatedRoute.paramMap) as any),
    {
      initialValue: ((this.activatedRoute.snapshot.queryParamMap ?? this.activatedRoute.snapshot.paramMap) as any),
    },
  );
  private readonly effectivePropId = computed(() => {
    const raw = (this.queryParamMap() as any)?.get('prop_id') as string | null | undefined;
    const fromUrl = raw ? Number(raw) : 0;
    if (Number.isFinite(fromUrl) && fromUrl > 0) return fromUrl;
    const ctx = this.propertyCtx.currentPropId();
    return Number.isFinite(ctx) && ctx > 0 ? ctx : 0;
  });

  readonly detailResource = httpResource<CheckOutDetailDto>(() => {
    const id = this.bookingId();
    if (!id) return undefined;
    const propId = this.effectivePropId();
    if (propId > 0) return `/management/check-outs/${id}/detail?prop_id=${propId}`;
    return undefined;
  });

  /**
   * Id-gate for the wizard init effect: pre-fills the 9 backend-derived
   * wizard fields exactly once per fetched `booking_id`. Reloads after
   * addCharge/quickCharge/completeCheckOut etc. don't reset user edits.
   */
  private lastInitializedId: string | null = null;

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

  // ── Late check-out (ventana gobernada por la política del hotel) ──
  /** Contexto resuelto por el servidor (is_late, cortesía, fee default). */
  readonly lateContext = computed(() => this.data()?.late_checkout_context ?? null);
  /** La salida supera la cortesía → requiere aprobación gerencial. */
  readonly lateRequiresApproval = computed(
    () => !!this.lateContext()?.is_late && !!this.lateContext()?.requires_approval,
  );
  /** El usuario puede aprobar la extensión (permiso manager-only). */
  readonly canApproveLate = computed(() => this.auth.hasPermission('check-ins.late_checkout_approve'));
  /** Sin permiso de aprobación y fuera de cortesía → el cierre queda bloqueado. */
  readonly lateBlocked = computed(() => this.lateRequiresApproval() && !this.canApproveLate());
  /** Modo elegido: '' (sin autorizar) | late_courtesy | late_approved. */
  readonly lateMode = signal<'late_courtesy' | 'late_approved' | ''>('');
  readonly lateReason = signal('');

  /** Coerción del select del panel: solo acepta los modos gobernados. */
  setLateMode(mode: string): void {
    this.lateMode.set(mode === 'late_approved' || mode === 'late_courtesy' ? mode : '');
  }

  /**
   * Modo CRUD reactivo: si algún campo del wizard difiere del estado guardado
   * en backend, el usuario está editando el check-out → UPDATE en el nav.
   */
  private readonly _opMode = computed<{ mode: OperationMode; detail: string }>(() => {
    const d = this.data();
    if (!d) return { mode: 'read', detail: '' };
    const edited =
      this.roomInspected() !== (d.check_out_room_inspected || false) ||
      this.keysReturned() !== (d.check_out_keys_returned || false) ||
      this.damagesFound() !== (d.check_out_damages_found || false) ||
      this.lateCheckoutFee() !== (d.check_out_late_checkout_fee || 0) ||
      this.discount() !== (d.check_out_discount || 0) ||
      this.discountReason() !== (d.check_out_discount_reason || '') ||
      this.paymentMethod() !== (d.check_out_payment_method || 'credit_card') ||
      this.paymentRef() !== (d.check_out_payment_ref || '') ||
      this.observations() !== (d.check_out_observations || '');
    return edited
      ? { mode: 'update', detail: `Check-out ${d.booking_id}` }
      : { mode: 'read', detail: '' };
  });

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
  readonly checkoutDone = computed(() => this.data()?.stay_status === STAY_CHECKED_OUT);

  // ── Guard: el check-out solo aplica a estancias con check-in activo ──
  // Una reserva que nunca registró check-in (no-show, pendiente o sin estado)
  // no tiene estancia que cerrar: se bloquea el wizard y se muestra el aviso.
  readonly neverCheckedIn = computed(() => {
    const d = this.data();
    if (!d) return false;
    return d.stay_status !== STAY_CHECKED_IN && d.stay_status !== STAY_CHECKED_OUT;
  });
  readonly noShowStay = computed(() => this.data()?.stay_status === STAY_NO_SHOW);

  // ── No-show manual (cierre desde recepción) ──
  readonly noShowPending = signal(false);
  /** Folio recién generado durante la sesión actual. */
  readonly noShowResult = signal<{ folio_number: string | null; penalty_amount: number } | null>(null);

  /**
   * Rebuild the no-show billing link from persisted checkout data after a
   * browser reload. The action response is only a fast path; ``folio`` and
   * ``no_show_penalty_amount`` are the durable source of truth.
   */
  readonly persistedNoShowResult = computed(() => {
    const d = this.data();
    if (!d || d.stay_status !== STAY_NO_SHOW) return null;
    if (!d.folio && d.no_show_penalty_amount == null) return null;
    return {
      folio_number: d.folio ?? null,
      penalty_amount: d.no_show_penalty_amount ?? 0,
    };
  });
  readonly displayedNoShowResult = computed(() => this.noShowResult() ?? this.persistedNoShowResult());

  /**
   * Botón de cierre: reserva sin check-in cuya estadía YA terminó (check-out
   * pasado) y que aún no fue marcada no-show. Gate por permiso
   * `reservations.update` — el mismo que exige el backend en el endpoint.
   */
  readonly canMarkNoShow = computed(() => {
    const d = this.data();
    if (!d || !this.neverCheckedIn()) return false;
    if (d.stay_status === STAY_NO_SHOW) return false;
    if (!d.check_out_date) return false;
    const checkOut = new Date(d.check_out_date + 'T00:00:00');
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    if (checkOut >= today) return false;
    return this.auth.hasPermission('reservations.update');
  });

  async markNoShow() {
    const d = this.data();
    if (!d || !this.canMarkNoShow() || this.noShowPending()) return;

    this.noShowPending.set(true);
    this.successMessage.set('');
    this.errorMessage.set('');
    try {
      // Flujo compartido: diálogo de confirmación → POST no-show → folio.
      const result = await this.noShow.markNoShowWithConfirm(d.booking_id, d.guest_name, d.prop_id);
      if (!result) return; // cancelado — el finally libera el pending
      this.successMessage.set(this.noShow.successMessage(result));
      this.noShowResult.set({
        folio_number: result.folio_number ?? null,
        penalty_amount: result.penalty_amount,
      });
      this.detailResource.reload();
    } catch (err) {
      this.errorMessage.set(getErrorMessage(err) || 'No fue posible marcar el no-show.');
    } finally {
      this.noShowPending.set(false);
    }
  }

  // ── Computed financials ──
  // Fuente de verdad de la liquidación: el breakdown MOSTRADO en el paso 3
  // (alojamiento + extras + late − descuento + impuestos). TOTAL y SALDO se
  // derivan SIEMPRE de aquí — nunca de ``invoice.subtotal``, que puede ser
  // anterior a los últimos cargos adicionales (stale) y haría que el TOTAL
  // mostrado no cuadrara con la suma de la tabla.
  readonly roomTotal = computed(() => this.data()?.total_price ?? 0);
  readonly chargesTotal = computed(() => this.data()?.charges_total ?? 0);
  readonly lateFee = computed(() => this.lateCheckoutFee());
  readonly discountVal = computed(() => this.discount());
  /** Breakdown antes de descuento: alojamiento + extras + late (lo que suma la tabla). */
  readonly breakdownSubtotal = computed(() =>
    Math.round((this.roomTotal() + this.chargesTotal() + this.lateFee()) * 100) / 100
  );
  readonly subtotal = computed(() =>
    Math.max(0, Math.round((this.breakdownSubtotal() - this.discountVal()) * 100) / 100)
  );
  /** La factura emitida (no cancelada) cubre el subtotal actual de la liquidación. */
  readonly invoiceCoversBreakdown = computed(() => {
    const inv = this.data()?.invoice;
    if (!inv || inv.status === 'cancelled') return false;
    return Number(inv.subtotal ?? 0) >= this.subtotal() - 0.005;
  });
  readonly taxes = computed(() => {
    const hasAdjustments = this.lateFee() > 0 || this.discountVal() > 0;
    const inv = this.data()?.invoice;
    // Impuestos fiscales de la factura SOLO si la factura cubre el breakdown
    // y no hubo ajustes posteriores; si quedó corta, IVA 16% sobre el subtotal vivo.
    if (!hasAdjustments && this.invoiceCoversBreakdown() && inv?.taxes) return inv.taxes;
    return Math.round(this.subtotal() * 0.16 * 100) / 100;
  });
  readonly grandTotal = computed(() => this.subtotal() + this.taxes());
  readonly depositDeducted = computed(() => {
    const d = this.data();
    if (!d) return 0;
    return d.deposit_received ? Math.round(this.roomTotal() * 0.5 * 100) / 100 : 0;
  });
  readonly hasExistingPayments = computed(() => {
    const d = this.data();
    return (d?.invoice?.paid_at && d.invoice.status === 'paid') ? true : false;
  });
  readonly totalPaid = computed(() => {
    if (this.hasExistingPayments()) return this.grandTotal();
    return this.depositDeducted();
  });
  /** SALDO = TOTAL − Pagado: siempre reconcilia con la fila Pagado mostrada
   *  (antes restaba el depósito aunque la factura estuviera pagada por el
   *  TOTAL completo → SALDO ≠ TOTAL − Pagado). */
  readonly balanceDue = computed(() =>
    Math.round((this.grandTotal() - this.totalPaid()) * 100) / 100
  );
  /** Nota de reconciliación: la factura emitida no cubre los cargos
   *  adicionales actuales (se registraron cargos después de facturar). El
   *  TOTAL incluye los cargos nuevos; la factura queda corta. El gap se mide
   *  contra ``covered_subtotal`` (suma de subtotales de TODAS las facturas
   *  no canceladas del booking): una factura complementaria del gap despeja
   *  la nota al recargar el detalle. */
  readonly invoiceReconcileNote = computed<{ invoice_number: string; gap: number } | null>(() => {
    const inv = this.data()?.invoice;
    if (!inv || inv.status === 'cancelled') return null;
    const covered = Number(inv.covered_subtotal ?? inv.subtotal ?? 0);
    const gap = Math.round((this.subtotal() - covered) * 100) / 100;
    if (gap <= 0) return null;
    return { invoice_number: inv.invoice_number || inv.id, gap };
  });

  readonly currency = computed(() => this.data()?.currency ?? 'USD');

  /** Responsible shift + cashier of the check-out (stamped at completion). */
  readonly checkOutShift = computed(() => this.data()?.check_out_shift ?? null);

  // ── Category entries for partials ──
  readonly chargeCategoryEntries = computed(() => {
    const d = this.data();
    if (!d?.charges_by_category) return [];
    return (Object.entries(d.charges_by_category) as [string, BookingCharge[]][]).map(([key, items]) => ({
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
    return d.charges.map((c: BookingCharge) => ({
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
    // Single effect: error → viewState('error'|'empty'),
    // first fetch → pre-fill backend-saved wizard fields (id-gated so reloads
    // after completeCheckOut/addCharge/removeCharge/quickCharge/onInvoiceEmitted
    // don't trash user-edited values).
    effect(() => {
      // Leer error() ANTES de value(): value() lanza cuando el request falló
      // (ej. 403) y este efecto se re-ejecuta durante el change detection →
      // el throw rompería la vista y spamearía la consola.
      const err = this.detailResource.error();
      if (err) {
        // getErrorStatus cubre HttpErrorResponse (tests) y ApiError del
        // interceptor (app en vivo) — ver shared/utils/http-error.util.ts.
        const status = getErrorStatus(err);
        // 403 check-outs.read → el rol no tiene permiso; no es un error del server.
        this.viewState.set(status === 403 ? 'forbidden' : (status === 404 ? 'empty' : 'error'));
        return;
      }

      const detail = this.detailResource.value();
      if (!detail) {
        this.viewState.set('loading');
        return;
      }
      if (this.lastInitializedId === detail.booking_id) return;
      this.lastInitializedId = detail.booking_id;

      this.roomInspected.set(detail.check_out_room_inspected || false);
      this.keysReturned.set(detail.check_out_keys_returned || false);
      this.damagesFound.set(detail.check_out_damages_found || false);
      // Fee late: el persistido del flujo gobernado manda; cae al manual legacy.
      this.lateCheckoutFee.set((detail.late_checkout_fee ?? detail.check_out_late_checkout_fee) || 0);
      this.discount.set(detail.check_out_discount || 0);
      this.discountReason.set(detail.check_out_discount_reason || '');
      this.paymentMethod.set(detail.check_out_payment_method || 'credit_card');
      this.paymentRef.set(detail.check_out_payment_ref || '');
      this.observations.set(detail.check_out_observations || '');
      this.canComplete.set(detail.assigned_rooms.length > 0 && detail.stay_status === STAY_CHECKED_IN);
      // Nueva reserva → limpiar el folio de un no-show anterior
      this.noShowResult.set(null);
      // Late check-out: pre-cargar la ventana gobernada (cortesía automática o
      // cargo default de la política para la aprobación gerencial).
      const lc = detail.late_checkout_context;
      if (lc?.is_late && detail.stay_status === STAY_CHECKED_IN) {
        this.lateMode.set(lc.requires_approval ? '' : 'late_courtesy');
        this.lateReason.set('');
        if (!lc.requires_approval) this.lateCheckoutFee.set(0);
        else if (this.lateCheckoutFee() === 0) this.lateCheckoutFee.set(lc.default_fee);
      } else {
        this.lateMode.set('');
        this.lateReason.set('');
      }
      if (detail.stay_status === STAY_CHECKED_OUT) this.currentStep.set(5);
      this.viewState.set('success');
    }, { allowSignalWrites: true });

    // Modo CRUD reactivo: editar campos del wizard → UPDATE en el nav.
    // El cleanup libera el overlay anterior al cambiar un campo y al destruir
    // la página; así no queda un modo de check-out en la siguiente ruta.
    effect((onCleanup) => {
      const m = this._opMode();
      if (m.mode === 'read') return;
      onCleanup(this.opMode.setTransientMode(m.mode, m.detail));
    }, { allowSignalWrites: true });
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

  onInvoiceEmitted(): void {
    if (!this.data()) return;
    this.detailResource.reload();
  }

  /** Tras emitir la factura complementaria del gap, recarga el detalle: la
   *  nota de reconciliación se despeja (covered_subtotal ahora cubre el
   *  subtotal vivo) y la complementaria queda registrada. */
  onComplementEmitted(): void {
    if (!this.data()) return;
    this.detailResource.reload();
  }

  removeCharge(chargeId: string): void {
    if (!chargeId) return;
    const propId = this.data()?.prop_id ?? 0;
    this.chargeSaving.set(true);
    this.api.deleteCharge(chargeId, propId).subscribe({
      next: () => {
        if (this.data()) this.detailResource.reload();
        this.chargeSaving.set(false);
      },
      error: () => this.chargeSaving.set(false),
    });
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
        this.detailResource.reload();
      },
      error: (err: ApiError) => {
        this.chargeSaving.set(false);
        this.chargeError.set(
          err.message || 'No se pudo crear el cargo. Revisá el concepto y el monto e intentá de nuevo.',
        );
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
        this.detailResource.reload();
      },
      error: () => { this.chargeSaving.set(false); },
    });
  }

  completeCheckOut(): void {
    const d = this.data();
    // A repeated click or a stale tab must not submit the terminal transition
    // again. The backend is idempotent too, but this keeps the UI quiet.
    if (!d || this.completing() || this.checkoutDone()) return;
    // Fuera de la cortesía y sin permiso de aprobación: el backend daría 403;
    // bloquear antes con un mensaje claro en el paso de liquidación.
    if (this.lateBlocked()) {
      this.completeError.set(
        'Este check-out supera la cortesía de salida y requiere aprobación del gerente. ' +
        'Derivalo a gerencia: solo un gerente de hotel puede autorizar la salida extendida y completar el check-out.',
      );
      return;
    }
    this.completing.set(true);
    this.completeError.set('');

    const lc = this.lateContext();
    const payload: Partial<CheckOutDetailSavePayload> & { split_invoice?: boolean } = {
      check_out_room_inspected: this.roomInspected(),
      check_out_keys_returned: this.keysReturned(),
      check_out_damages_found: this.damagesFound(),
      check_out_discount: this.discount(),
      check_out_discount_reason: this.discountReason(),
      check_out_payment_method: this.paymentMethod(),
      check_out_payment_ref: this.paymentRef(),
      check_out_observations: this.observations(),
      split_invoice: this.splitInvoice(),
    };
    if (lc?.is_late) {
      // La ventana gobernada manda: dentro de cortesía se registra late_courtesy
      // (fee 0); fuera, el modo lo decide el aprobador con motivo + cargo.
      payload.late_checkout_mode = this.lateMode() || (lc.requires_approval ? '' : 'late_courtesy');
      payload.late_checkout_approved = this.lateMode() === 'late_approved';
      payload.late_checkout_reason = this.lateReason();
      payload.late_checkout_fee = this.lateMode() === 'late_approved' ? this.lateCheckoutFee() : 0;
    }

    this.api.completeCheckOutWithDetail(d.booking_id, payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (result) => {
        this.completing.set(false);
        this.canComplete.set(false);
        // Fee derivado del reloj → la vista completada lo muestra real.
        if (result.late_checkout_fee != null) this.lateCheckoutFee.set(result.late_checkout_fee);
        this.goToStep(5);
        // Refresh detail; the init effect's id-gate preserves user edits
        // across this refetch.
        this.detailResource.reload();
      },
      error: (err: ApiError) => {
        this.completing.set(false);
        this.completeError.set(
          err.message ||
          'No se pudo completar el check-out. Revisá el saldo y los cargos pendientes e intentá de nuevo.',
        );
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
