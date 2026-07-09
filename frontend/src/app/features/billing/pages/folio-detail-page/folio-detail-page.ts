import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { switchMap } from 'rxjs';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { FolioApiService, type FolioCategory, type FolioViewModel, type FolioPosting } from '../../services/folio-api.service';

@Component({
  selector: 'app-folio-detail-page',
  imports: [DatePipe, FormsModule, ErrorStateComponent, LoadingStateComponent],
  templateUrl: './folio-detail-page.html',
  styleUrl: './folio-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FolioDetailPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly folioApi = inject(FolioApiService);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly folio = signal<FolioViewModel | null>(null);
  readonly categories = signal<FolioCategory[]>([]);
  readonly actionError = signal<string | null>(null);
  readonly actionMessage = signal<string | null>(null);
  readonly postingMode = signal<'idle' | 'charge' | 'discount'>('idle');
  readonly postingBusy = signal(false);

  // Posting form
  readonly postForm = signal({
    category: 'restaurante',
    concept: '',
    amount: 0,
    quantity: 1,
  });

  readonly isOpen = computed(() => this.folio()?.status === 'open');
  readonly isClosed = computed(() => this.folio()?.status === 'closed');
  readonly postingCount = computed(() => this.folio()?.postingCount ?? 0);

  /** Status label: Activo / Vencido / Cerrado s/factura / Facturado */
  readonly statusLabel = computed(() => {
    const f = this.folio();
    if (!f) return '';
    if (f.status === 'open' && f.isExpired) return 'Vencido';
    if (f.status === 'open') return 'Activo';
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
    if (f.status === 'closed' && !f.hasInvoice) return 'closed-no-invoice';
    if (f.status === 'closed' && f.hasInvoice) return 'invoiced';
    return 'closed';
  });

  // Group postings by category for display
  readonly postingsByCategory = computed(() => {
    const p = this.folio()?.postings ?? [];
    const groups = new Map<string, FolioPosting[]>();
    // Order: room first, then charges, then discounts, then payments
    const typeOrder: Record<string, number> = { room: 0, charge: 1, discount: 2, payment: 3, adjustment: 4 };
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
    // Load categories
    this.folioApi.getCategories().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (cats) => this.categories.set(cats),
      error: () => {},
    });

    // Load folio
    this.activatedRoute.paramMap
      .pipe(
        switchMap((params) => {
          this.viewState.set('loading');
          this.postingMode.set('idle');
          return this.folioApi.getFolio(params.get('bookingId')!);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (data) => {
          this.folio.set(data);
          this.viewState.set('success');
        },
        error: () => this.viewState.set('error'),
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
      next: (updated) => {
        this.folio.set(updated);
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

  closeFolio(): void {
    if (!this.folio()?.bookingId) return;
    this.actionError.set(null);
    this.actionMessage.set(null);
    this.postingBusy.set(true);

    this.folioApi.closeFolio(this.folio()!.bookingId).subscribe({
      next: (updated) => {
        this.folio.set(updated);
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
