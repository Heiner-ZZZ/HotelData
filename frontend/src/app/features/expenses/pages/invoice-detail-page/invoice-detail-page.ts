import { CurrencyPipe, DatePipe } from '@angular/common';
import { HttpErrorResponse, httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';

import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { ExpensesApiService } from '../../services/expenses-api.service';

@Component({
  selector: 'app-invoice-detail-page',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, PageHeaderComponent, LoadingStateComponent],
  styleUrl: '../../expenses.shared.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page-wrap page-wrap--narrow">
      <app-page-header eyebrow="Gastos" title="Detalle de Factura" description="Información completa de la factura." />

      <button class="back-btn" type="button" (click)="goBack()">
        <span class="material-symbols-outlined icon">arrow_back</span> Volver
      </button>

      @switch (viewState()) {
        @case ('loading') { <app-loading-state label="Cargando factura..." /> }
        @case ('error') { <div class="error-line">Error al cargar la factura.</div> }
        @default {
          @if (inv(); as i) {
            <!-- Status Banner (theme-aware via .status-banner--<status>) -->
            <div class="status-banner" [class]="'status-banner status-banner--' + i.status">
              <span class="material-symbols-outlined">{{ statusIcon(i.status) }}</span>
              <span style="font-weight: 500;">{{ statusText(i.status) }}</span>
            </div>

            <div class="meta-grid">
              <!-- Vendor -->
              <div class="meta-tile">
                <h4 class="meta-tile__heading">Proveedor</h4>
                <p class="meta-tile__primary">{{ i.vendorName }}</p>
                <p class="meta-tile__secondary">{{ i.category }}</p>
              </div>
              <!-- Amount -->
              <div class="meta-tile">
                <h4 class="meta-tile__heading">Total</h4>
                <p class="meta-tile__total">{{ i.total | currency:'MXN':'symbol-narrow':'1.2-2' }}</p>
                <p class="meta-tile__secondary">Subtotal: {{ i.amount | currency:'MXN':'symbol-narrow' }} + IVA: {{ i.taxAmount | currency:'MXN':'symbol-narrow' }}</p>
              </div>

              <!-- Details -->
              <div class="meta-tile meta-tile--full">
                <h4 class="meta-tile__heading">Detalles</h4>
                <div class="meta-row">
                  <div><span class="meta-row__label">Descripción:</span> <span class="meta-row__value">{{ i.description || '—' }}</span></div>
                  <div><span class="meta-row__label">Factura:</span> <span class="meta-row__value">{{ i.invoiceDate || '—' }}</span></div>
                  <div><span class="meta-row__label">Vencimiento:</span> <span class="meta-row__value">{{ i.dueDate || '—' }}</span></div>
                  <div><span class="meta-row__label">Creada:</span> <span class="meta-row__value">{{ i.createdAt | date:'dd/MM/yyyy HH:mm' }}</span></div>
                  @if (i.approvedBy) {
                    <div class="meta-row--full"><span class="meta-row__label">Aprobada por:</span> <span class="meta-row__value">{{ i.approvedBy }}</span></div>
                  }
                  @if (i.notes) {
                    <div class="meta-row--full"><span class="meta-row__label">Notas:</span> <span class="meta-row__value">{{ i.notes }}</span></div>
                  }
                </div>
              </div>

              <!-- Actions -->
              @if (i.status === 'pending') {
                <div class="meta-actions">
                  <button class="btn btn--lg btn--ghost-danger" type="button" (click)="updateStatus(i.id, 'rejected')">Rechazar</button>
                  <button class="btn btn--lg btn--success" type="button" (click)="updateStatus(i.id, 'approved')">Aprobar</button>
                  <button class="btn btn--lg btn--primary" type="button" (click)="updateStatus(i.id, 'paid')">Marcar Pagada</button>
                </div>
              }
              @if (i.status === 'approved') {
                <div class="meta-actions">
                  <button class="btn btn--lg btn--primary" type="button" (click)="updateStatus(i.id, 'paid')">Marcar Pagada</button>
                </div>
              }
            </div>
          }
        }
      }
    </div>
  `
})
export class InvoiceDetailPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(ExpensesApiService);

  // ── Reactive route param — httpResource re-fires when this changes ──
  private readonly paramMap = toSignal(this.route.paramMap, {
    initialValue: this.route.snapshot.paramMap,
  });
  readonly invId = computed(() => this.paramMap().get('invoiceId') ?? '');

  readonly detailResource = httpResource<any>(() => {
    const id = this.invId();
    return id ? `/api/expenses/invoices/${id}` : undefined;
  });

  readonly inv = computed(() => this.detailResource.value() ?? null);

  readonly viewState = computed<'loading' | 'success' | 'error' | 'empty'>(() => {
    const v = this.detailResource.value();
    // Anti-flicker: keep 'success' during silent reloads after mutations
    // (updateStatus() → detailResource.reload() triggers a brief isLoading).
    if (this.detailResource.isLoading() && !v) return 'loading';
    const err = this.detailResource.error();
    if (err instanceof HttpErrorResponse) return err.status === 404 ? 'empty' : 'error';
    if (err) return 'error';
    return v ? 'success' : 'loading';
  });

  goBack() { this.router.navigate(['/management/expenses/invoices']); }

  updateStatus(id: string, status: string) {
    // Server-side update; httpResource reload picks up the new value and
    // re-renders the template via `inv()` (computed).
    this.api.updateInvoice(id, { status }).subscribe({
      next: () => { this.detailResource.reload(); },
    });
  }

  statusIcon(s: string) {
    const map: any = { pending: 'pending', approved: 'check_circle', paid: 'payments', rejected: 'cancel' };
    return map[s] || 'info';
  }
  statusText(s: string) {
    const map: any = { pending: 'Pendiente de aprobación', approved: 'Aprobada', paid: 'Pagada', rejected: 'Rechazada' };
    return map[s] || s;
  }
}
