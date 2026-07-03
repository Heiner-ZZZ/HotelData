import { CurrencyPipe, DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { switchMap } from 'rxjs';

import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { ExpensesApiService } from '../../services/expenses-api.service';

@Component({
  selector: 'app-invoice-detail-page',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, PageHeaderComponent, LoadingStateComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div style="max-width: 700px; margin: 0 auto; padding: 24px;">
      <app-page-header eyebrow="Gastos" title="Detalle de Factura" description="Información completa de la factura." />

      <button (click)="goBack()" style="display: inline-flex; align-items: center; gap: 6px; background: none; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 16px; font-size: 13px; cursor: pointer; margin-bottom: 16px; color: #475569;">
        <span class="material-symbols-outlined" style="font-size: 16px;">arrow_back</span> Volver
      </button>

      @switch (viewState()) {
        @case ('loading') { <app-loading-state label="Cargando factura..." /> }
        @case ('error') { <div style="text-align: center; padding: 24px; color: #dc2626;">Error al cargar la factura.</div> }
        @default {
          @if (inv(); as i) {
            <!-- Status Banner -->
            <div [style]="'padding: 12px 16px; border-radius: 10px; margin-bottom: 20px; display: flex; align-items: center; gap: 8px; ' + statusBannerStyle(i.status)">
              <span class="material-symbols-outlined">{{ statusIcon(i.status) }}</span>
              <span style="font-weight: 500;">{{ statusText(i.status) }}</span>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
              <!-- Vendor & Amount -->
              <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px;">
                <h4 style="font-size: 13px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.03em; margin: 0 0 16px;">Proveedor</h4>
                <p style="font-size: 18px; font-weight: 700; color: #0f172a; margin: 0 0 4px;">{{ i.vendorName }}</p>
                <p style="font-size: 13px; color: #64748b; margin: 0;">{{ i.category }}</p>
              </div>
              <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px;">
                <h4 style="font-size: 13px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.03em; margin: 0 0 16px;">Total</h4>
                <p style="font-size: 24px; font-weight: 700; color: #0f172a; margin: 0;">{{ i.total | currency:'MXN':'symbol-narrow':'1.2-2' }}</p>
                <p style="font-size: 12px; color: #64748b; margin: 2px 0 0;">Subtotal: {{ i.amount | currency:'MXN':'symbol-narrow' }} + IVA: {{ i.taxAmount | currency:'MXN':'symbol-narrow' }}</p>
              </div>

              <!-- Details -->
              <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; grid-column: 1 / -1;">
                <h4 style="font-size: 13px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.03em; margin: 0 0 16px;">Detalles</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 13px;">
                  <div><span style="color: #64748b;">Descripción:</span> <span style="color: #0f172a;">{{ i.description || '—' }}</span></div>
                  <div><span style="color: #64748b;">Factura:</span> <span style="color: #0f172a;">{{ i.invoiceDate || '—' }}</span></div>
                  <div><span style="color: #64748b;">Vencimiento:</span> <span style="color: #0f172a;">{{ i.dueDate || '—' }}</span></div>
                  <div><span style="color: #64748b;">Creada:</span> <span style="color: #0f172a;">{{ i.createdAt | date:'dd/MM/yyyy HH:mm' }}</span></div>
                  @if (i.approvedBy) {
                    <div><span style="color: #64748b;">Aprobada por:</span> <span style="color: #0f172a;">{{ i.approvedBy }}</span></div>
                  }
                  @if (i.notes) {
                    <div style="grid-column: 1 / -1;"><span style="color: #64748b;">Notas:</span> <span style="color: #0f172a;">{{ i.notes }}</span></div>
                  }
                </div>
              </div>

              <!-- Actions -->
              @if (i.status === 'pending') {
                <div style="grid-column: 1 / -1; display: flex; gap: 12px; justify-content: flex-end;">
                  <button (click)="updateStatus(i.id, 'rejected')"
                    style="padding: 10px 20px; background: white; border: 1px solid #dc2626; color: #dc2626; border-radius: 8px; font-size: 13px; cursor: pointer;">Rechazar</button>
                  <button (click)="updateStatus(i.id, 'approved')"
                    style="padding: 10px 20px; background: #16a34a; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer;">Aprobar</button>
                  <button (click)="updateStatus(i.id, 'paid')"
                    style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer;">Marcar Pagada</button>
                </div>
              }
              @if (i.status === 'approved') {
                <div style="grid-column: 1 / -1; display: flex; gap: 12px; justify-content: flex-end;">
                  <button (click)="updateStatus(i.id, 'paid')"
                    style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer;">Marcar Pagada</button>
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
  private readonly destroyRef = inject(DestroyRef);
  private readonly api = inject(ExpensesApiService);

  readonly viewState = signal<'loading' | 'success' | 'error'>('loading');
  readonly inv = signal<any>(null);

  constructor() {
    this.route.paramMap.pipe(
      switchMap(params => {
        this.viewState.set('loading');
        return this.api.getInvoice(params.get('invoiceId')!);
      }),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (data) => { this.inv.set(data); this.viewState.set('success'); },
      error: () => this.viewState.set('error'),
    });
  }

  goBack() { this.router.navigate(['/management/expenses/invoices']); }

  updateStatus(id: string, status: string) {
    this.api.updateInvoice(id, { status }).subscribe({
      next: (updated: any) => { this.inv.set(updated); },
    });
  }

  statusBannerStyle(s: string) {
    const map: any = { pending: 'background:#fefce8;color:#a16207;border:1px solid #fde68a;', approved: 'background:#f0fdf4;color:#166534;border:1px solid #bbf7d0;', paid: 'background:#eff6ff;color:#1d4ed8;border:1px solid #bfdbfe;', rejected: 'background:#fef2f2;color:#991b1b;border:1px solid #fecaca;' };
    return map[s] || '';
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
