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
import { FolioApiService, getFolioCloseState, mapFolio, type FolioCategory, type FolioViewModel, type FolioPosting, type FolioDto, type FolioSettlementType } from '../../services/folio-api.service';

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

  // Group postings by category for display
  readonly postingsByCategory = computed(() => {
    const p = this.folio()?.postings ?? [];
    const groups = new Map<string, FolioPosting[]>();
    // Order: room first, then charges, then discounts, then payments
    const typeOrder: Record<string, number> = { room: 0, charge: 1, charge_reversal: 2, refund: 3, discount: 4, payment: 5, adjustment: 6 };
    for (const posting of p) {
      const key = posting.category || 'Otros';
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

  categoryIcon(catId: string): string {
    const map: Record<string, string> = {
      habitacion: 'bed',
      restaurante: 'restaurant',
      bar: 'local_bar',
      room_service: 'room_service',
      minibar: 'kitchen',
      spa: 'spa',
      lavanderia: 'local_laundry_service',
      parking: 'local_parking',
      mascotas: 'pets',
      llamadas: 'phone',
      danos: 'warning',
      late_checkout: 'schedule',
      descuento: 'sell',
      otros: 'more_horiz',
    };
    return map[catId] ?? 'receipt_long';
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

  startSettlement(mode: FolioSettlementType): void {
    const folio = this.folio();
    if (!folio || folio.totalDue <= 0.005) return;
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
      this.actionError.set('El pago debe ser positivo y no exceder el saldo pendiente.');
      return;
    }
    if (mode !== 'payment' && (!form.reason.trim() || !form.approvalReference.trim())) {
      this.actionError.set('La razón y la referencia de aprobación son obligatorias.');
      return;
    }
    if (mode === 'external_settlement' && !form.externalReference.trim()) {
      this.actionError.set('La referencia externa es obligatoria.');
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
        this.actionError.set('No se pudo registrar la liquidación. El saldo no se cerró ambiguamente.');
        this.postingBusy.set(false);
      },
    });
  }

  submitPosting(): void {
    const form = this.postForm();
    if (!form.concept || form.amount <= 0) {
      this.actionError.set('El concepto y el monto son obligatorios.');
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
        this.actionError.set('No se pudo registrar la operación en el folio.');
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
        this.actionError.set('No se pudo reabrir el folio.');
        this.postingBusy.set(false);
      },
    });
  }

  closeFolio(): void {
    const folio = this.folio();
    if (!folio?.bookingId) return;
    if (getFolioCloseState(folio) !== 'ready') {
      this.actionError.set('No se puede cerrar el folio mientras tenga saldo pendiente.');
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
      error: () => {
        this.actionError.set('No se pudo cerrar el folio.');
        this.postingBusy.set(false);
      },
    });
  }

  goBack(): void {
    void this.router.navigate(['/management/billing/invoices']);
  }

  readonly Math = Math;
}
