import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { distinctUntilChanged, map } from 'rxjs';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ApiError } from '../../../../core/api/api-error.model';
import { AuthService } from '../../../../core/auth/auth.service';
import { BILLING_WRITE_OFF_APPROVE } from '../../../../core/auth/permission.constants';
import { FolioApiService, getFolioCloseState, getFolioReconciliationNote, mapFolio, type FolioCategory, type FolioViewModel, type FolioPosting, type FolioDto, type FolioSettlementType } from '../../services/folio-api.service';

@Component({
  selector: 'app-folio-detail-page',
  imports: [DatePipe, FormsModule, ErrorStateComponent, LoadingStateComponent],
  templateUrl: './folio-detail-page.html',
  styleUrl: './folio-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FolioDetailPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly folioApi = inject(FolioApiService);
  private readonly router = inject(Router);
  private readonly auth = inject(AuthService);

  /**
   * Autorización de supervisor para cierres de excepción (write-off / cortesía /
   * settlement externo). Lee el permiso del catálogo vía /auth/me — nunca roles
   * hardcodeados — igual que el gate del backend (billing.write_off.approve).
   */
  readonly canApproveWriteOff = computed(() => this.auth.hasPermission(BILLING_WRITE_OFF_APPROVE));

  private readonly bookingId = toSignal(
    this.activatedRoute.paramMap.pipe(
      map((params) => params.get('bookingId') ?? ''),
      distinctUntilChanged(),
    ),
    { initialValue: '' }
  );

  readonly categoriesResource = httpResource<FolioCategory[]>(() => '/api/billing/folios/categories');
  readonly categories = computed(() => this.categoriesResource.value() ?? []);

  readonly folioResource = httpResource<FolioViewModel>(() => {
    const id = this.bookingId();
    return id ? `/api/billing/folios/${id}` : undefined;
  }, {
    parse: (dto) => mapFolio(dto as FolioDto),
  });
  readonly folio = computed(() => this.folioResource.value() ?? null);
  readonly viewState = computed<ViewState>(() => {
    if (this.folioResource.isLoading()) return 'loading';
    if (this.folioResource.error()) return 'error';
    return this.folio() ? 'success' : 'loading';
  });

  readonly actionError = signal<string | null>(null);
  readonly actionMessage = signal<string | null>(null);
  readonly postingMode = signal<'idle' | 'charge' | 'discount'>('idle');
  readonly postingBusy = signal(false);
  readonly complementing = signal(false);
  readonly settlementMode = signal<'idle' | FolioSettlementType>('idle');
  readonly settlementForm = signal({
    amount: 0,
    method: 'card',
    reason: '',
    approvalReference: '',
    externalReference: '',
    idempotencyKey: '',
  });

  // Posting form
  readonly postForm = signal({
    category: 'restaurante',
    concept: '',
    amount: 0,
    quantity: 1,
  });

  readonly isOpen = computed(() => this.folio()?.status === 'open');
  readonly isClosed = computed(() => this.folio()?.status === 'closed');
  readonly closeState = computed(() => getFolioCloseState(this.folio()));
  readonly canReopen = computed(() => {
    const f = this.folio();
    return f?.status === 'closed' && f.totalDue > 0.005;
  });
  readonly postingCount = computed(() => this.folio()?.postingCount ?? 0);
  /** Reconciliation note shared with check-out: active folio charges beyond
   * the subtotal covered by the main + complementary invoices. */
  readonly reconcileNote = computed(() => getFolioReconciliationNote(this.folio()));

  /** Status label: Activo / Vencido / Cerrado s/factura / Facturado */
  readonly statusLabel = computed(() => {
    const f = this.folio();
    if (!f) return '';
    if (f.status === 'open' && f.reopenedAt) return 'Reabierto para cobro';
    if (f.status === 'open' && f.isExpired) return 'Vencido';
    if (f.status === 'open') return 'Activo';
    if (f.status === 'settled') return 'Liquidado';
    if (f.status === 'written_off') return 'Castigado';
    if (f.status === 'refunded') return 'Reembolsado';
    if (f.status === 'closed' && f.closeReason) return `Cerrado: ${f.closeReason.split(':')[0]}`;
    if (f.status === 'closed' && !f.hasInvoice) return 'Cerrado s/factura';
    if (f.status === 'closed' && f.hasInvoice) return 'Facturado';
    return 'Cerrado';
  });

  /** Status CSS class */
  readonly statusClass = computed(() => {
    const f = this.folio();
    if (!f) return '';
    if (f.status === 'open' && f.isExpired) return 'expired';
    if (f.status === 'open') return 'open';
    if (f.status === 'settled') return 'settled';
    if (f.status === 'written_off') return 'written-off';
    if (f.status === 'refunded') return 'refunded';
    if (f.status === 'closed' && !f.hasInvoice) return 'closed-no-invoice';
    if (f.status === 'closed' && f.hasInvoice) return 'invoiced';
    return 'closed';
  });

  // Group postings by category for display.
  // El key es el id canónico del catálogo cuando el posting lo trae (postings
  // automáticos estandarizados); para postings legados que solo guardan el
  // label (o el id en ``category``, quirk histórico de los manuales), el key
  // es ese string — categoryIcon/categoryLabel resuelven por ambos caminos.
  readonly postingsByCategory = computed(() => {
    const p = this.folio()?.postings ?? [];
    const groups = new Map<string, FolioPosting[]>();
    // Order: room first, then charges, then discounts, then payments
    const typeOrder: Record<string, number> = { room: 0, charge: 1, charge_reversal: 2, refund: 3, discount: 4, payment: 5, adjustment: 6 };
    for (const posting of p) {
      const key = posting.categoryId ?? (posting.category || 'otros');
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(posting);
    }
    // Return sorted entries
    return Array.from(groups.entries()).sort((a, b) => {
      const typeA = a[1][0]?.type ?? '';
      const typeB = b[1][0]?.type ?? '';
      return (typeOrder[typeA] ?? 99) - (typeOrder[typeB] ?? 99);
    });
  });

  /** Índices derivados del catálogo servido por el backend. */
  private readonly categoryById = computed(() =>
    new Map(this.categories().map((category) => [category.id, category])),
  );
  private readonly categoryByLabel = computed(() =>
    new Map(this.categories().map((category) => [this.normalizeCategoryLabel(category.label), category])),
  );
  /** Legacy labels are aliases only; displayed metadata still comes from the API catalog. */
  private readonly legacyCategoryAliases: Record<string, string> = {
    penalizacion: 'no_show',
  };

  /**
   * Normaliza únicamente para encontrar postings legacy por su label. El label y
   * el icono mostrados siempre provienen de la entrada remota del catálogo.
   */
  private normalizeCategoryLabel(value: string): string {
    return value.trim().normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  }

  private resolveCategory(value: string): FolioCategory | undefined {
    const normalized = this.normalizeCategoryLabel(value);
    const aliasedId = this.legacyCategoryAliases[normalized];
    return this.categoryById().get(value)
      ?? this.categoryByLabel().get(normalized)
      ?? (aliasedId ? this.categoryById().get(aliasedId) : undefined);
  }

  /** Icono por id canónico o label legacy, resuelto desde el catálogo remoto. */
  categoryIcon(categoryKey: string): string {
    return this.resolveCategory(categoryKey)?.icon ?? 'receipt_long';
  }

  /** Label por id canónico o label legacy, resuelto desde el catálogo remoto. */
  categoryLabel(categoryKey: string): string {
    return this.resolveCategory(categoryKey)?.label ?? categoryKey;
  }

  postingIcon(type: string): string {
    const map: Record<string, string> = {
      room: 'bed',
      charge: 'add_circle',
      discount: 'sell',
      payment: 'payments',
      charge_reversal: 'undo',
      refund: 'currency_exchange',
      adjustment: 'tune',
    };
    return map[type] ?? 'receipt_long';
  }

  typeLabel(type: string): string {
    const map: Record<string, string> = {
      room: 'Habitación',
      charge: 'Cargo',
      discount: 'Descuento',
      payment: 'Pago',
      charge_reversal: 'Anulación de cargo',
      refund: 'Reembolso',
      adjustment: 'Ajuste',
    };
    return map[type] ?? type;
  }

  readonly isPositive = (amount: number): boolean => amount > 0;

  /** Compute the sum of amounts for a group of postings (used in template). */
  _computeGroupTotal(postings: FolioPosting[]): number {
    return postings.reduce((sum, p) => sum + p.amount, 0);
  }

  constructor() {
    effect(() => {
      // Reset posting mode when bookingId changes
      this.bookingId();
      this.postingMode.set('idle');
    });
  }

  startPosting(mode: 'charge' | 'discount'): void {
    this.postingMode.set(mode);
    this.actionError.set(null);
    this.postForm.set({ category: mode === 'discount' ? 'descuento' : 'restaurante', concept: '', amount: 0, quantity: 1 });
  }

  cancelPosting(): void {
    this.postingMode.set('idle');
  }

  /** Emit the complementary invoice directly from Billing for the current gap. */
  emitComplementInvoice(): void {
    const folio = this.folio();
    const note = this.reconcileNote();
    if (!folio || !note || this.complementing()) return;

    this.complementing.set(true);
    this.actionError.set(null);
    this.actionMessage.set(null);
    this.folioApi.emitComplementInvoice(folio.bookingId, folio.propId).subscribe({
      next: (invoice) => {
        this.folioResource.reload();
        this.actionMessage.set(`Factura complementaria ${invoice.invoice_number} emitida para cubrir el gap sin facturar.`);
        this.complementing.set(false);
      },
      error: (err: ApiError) => {
        this.actionError.set(
          err?.message ||
          'No se pudo emitir la factura complementaria. Verificá que haya cargos nuevos sin facturar y un turno de caja activo, e intentá de nuevo.',
        );
        this.complementing.set(false);
      },
    });
  }

  startSettlement(mode: FolioSettlementType): void {
    const folio = this.folio();
    if (!folio || folio.totalDue <= 0.005) return;
    // Los cierres de excepción exigen aprobación de supervisor (mismo gate del backend).
    if (mode !== 'payment' && !this.canApproveWriteOff()) {
      this.actionError.set(
        'El cierre por excepción (write-off / cortesía / settlement externo) requiere aprobación del gerente. ' +
        'Registrá el pago del saldo o derivá el folio al gerente para que lo autorice.',
      );
      return;
    }
    this.settlementMode.set(mode);
    this.actionError.set(null);
    this.actionMessage.set(null);
    this.settlementForm.set({
      amount: mode === 'payment' ? folio.totalDue : folio.totalDue,
      method: 'card',
      reason: '',
      approvalReference: '',
      externalReference: '',
      idempotencyKey: `settlement-${folio.id}-${Date.now()}`,
    });
  }

  cancelSettlement(): void {
    this.settlementMode.set('idle');
  }

  submitSettlement(): void {
    const folio = this.folio();
    const mode = this.settlementMode();
    const form = this.settlementForm();
    if (!folio || mode === 'idle') return;
    if (mode === 'payment' && (!form.method || form.amount <= 0 || form.amount > folio.totalDue + 0.005)) {
      this.actionError.set(
        'El pago debe ser positivo y no exceder el saldo pendiente. ' +
        `Ingresá un monto entre $0.01 y $${folio.totalDue.toFixed(2)}.`,
      );
      return;
    }
    if (mode !== 'payment' && (!form.reason.trim() || !form.approvalReference.trim())) {
      this.actionError.set('La razón y la referencia de aprobación son obligatorias: escribí ambas antes de confirmar la liquidación.');
      return;
    }
    if (mode === 'external_settlement' && !form.externalReference.trim()) {
      this.actionError.set('La referencia externa es obligatoria: documentá el identificador del convenio antes de confirmar.');
      return;
    }

    const payload = {
      settlement_type: mode,
      idempotency_key: form.idempotencyKey,
      ...(mode === 'payment' ? { amount: form.amount, method: form.method } : {}),
      ...(mode !== 'payment' ? {
        reason: form.reason.trim(),
        approval_reference: form.approvalReference.trim(),
        ...(mode === 'external_settlement' ? { external_reference: form.externalReference.trim() } : {}),
      } : {}),
    };
    this.postingBusy.set(true);
    this.actionError.set(null);
    this.actionMessage.set(null);
    this.folioApi.settleFolio(folio.bookingId, payload).subscribe({
      next: (updated) => {
        this.folioResource.reload();
        this.settlementMode.set('idle');
        this.actionMessage.set(updated.status === 'open'
          ? 'Pago parcial registrado; el folio permanece abierto.'
          : 'Liquidación registrada y folio cerrado con trazabilidad.');
        this.postingBusy.set(false);
      },
      error: () => {
        this.actionError.set('No se pudo registrar la liquidación. Verificá el monto y el método de pago, e intentá de nuevo.');
        this.postingBusy.set(false);
      },
    });
  }

  submitPosting(): void {
    const form = this.postForm();
    if (!form.concept || form.amount <= 0) {
      this.actionError.set('El concepto y el monto son obligatorios. Completá ambos campos para registrar la operación.');
      return;
    }

    this.postingBusy.set(true);
    this.actionError.set(null);
    this.actionMessage.set(null);

    this.folioApi.postToFolio(this.folio()!.bookingId, {
      posting_type: this.postingMode() as 'charge' | 'discount',
      category: form.category,
      concept: form.concept,
      amount: this.postingMode() === 'discount' ? -Math.abs(form.amount) : form.amount,
      quantity: form.quantity,
      reference_type: 'manual',
    }).subscribe({
      next: () => {
        this.folioResource.reload();
        this.actionMessage.set(this.postingMode() === 'charge' ? 'Cargo registrado en el folio.' : 'Descuento aplicado al folio.');
        this.postingMode.set('idle');
        this.postingBusy.set(false);
      },
      error: () => {
        this.actionError.set('No se pudo registrar la operación en el folio. Verificá que haya un turno de caja activo y que el folio esté abierto, e intentá de nuevo.');
        this.postingBusy.set(false);
      },
    });
  }

  reopenFolio(): void {
    const folio = this.folio();
    if (!folio || !this.canReopen()) return;
    this.postingBusy.set(true);
    this.actionError.set(null);
    this.actionMessage.set(null);
    this.folioApi.reopenFolio(folio.bookingId).subscribe({
      next: () => {
        this.folioResource.reload();
        this.actionMessage.set('Folio reabierto para cobrar el saldo pendiente.');
        this.postingBusy.set(false);
      },
      error: () => {
        this.actionError.set('No se pudo reabrir el folio. Verificá que el folio esté cerrado con saldo pendiente cobrable e intentá de nuevo.');
        this.postingBusy.set(false);
      },
    });
  }

  closeFolio(): void {
    const folio = this.folio();
    if (!folio?.bookingId) return;
    if (getFolioCloseState(folio) !== 'ready') {
      this.actionError.set(
        'No se puede cerrar el folio mientras tenga saldo pendiente: ' +
        'registrá el pago del saldo o resolvelo con un write-off / liquidación externa aprobado antes de cerrar.',
      );
      return;
    }
    this.actionError.set(null);
    this.actionMessage.set(null);
    this.postingBusy.set(true);

    this.folioApi.closeFolio(this.folio()!.bookingId).subscribe({
      next: () => {
        this.folioResource.reload();
        this.actionMessage.set('Folio cerrado correctamente.');
        this.postingBusy.set(false);
      },
      error: (err: ApiError) => {
        this.actionError.set(
          err?.message ||
          'No se pudo cerrar el folio: registrá el saldo pendiente o pedile a un supervisor que autorice un cierre de excepción (write-off / cortesía / settlement externo).',
        );
        this.postingBusy.set(false);
      },
    });
  }

  goBack(): void {
    void this.router.navigate(['/management/billing/invoices']);
  }

  printPage(): void {
    window.print();
  }

  /** Responsible cashier label for a shift-stamped posting, or null. */
  shiftLabel(p: FolioPosting): string | null {
    return p.shiftEmployee || p.shiftOpenedBy || null;
  }

  /** Human label of the shift type ("Matutino" / "Vespertino" / "Nocturno"). */
  shiftTypeLabel(type: string | null): string {
    const map: Record<string, string> = {
      morning: 'Matutino',
      afternoon: 'Vespertino',
      evening: 'Nocturno',
    };
    return (type && map[type]) || '';
  }

  /** Tooltip with the shift FK + type for full attribution. */
  shiftTitle(p: FolioPosting): string {
    const type = p.shiftType ? ` · ${p.shiftType}` : '';
    return p.shiftId ? `Turno ${p.shiftId}${type}` : 'Sin turno asociado';
  }

  readonly Math = Math;
}
