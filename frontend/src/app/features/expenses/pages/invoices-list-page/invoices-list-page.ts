import { CurrencyPipe, DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';

import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ExpensesApiService } from '../../services/expenses-api.service';

@Component({
  selector: 'app-invoices-list-page',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, RouterLink, FormsModule, PageHeaderComponent, LoadingStateComponent, EmptyStateComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div style="max-width: 1200px; margin: 0 auto; padding: 24px;">
      <app-page-header eyebrow="Gastos" title="Facturas y Compras" description="Registro de facturas, aprobaciones y pagos." />

      <div style="display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; align-items: center;">
        <div style="flex: 1; min-width: 200px;">
          <input type="text" [(ngModel)]="searchVendor" (input)="loadInvoices()" placeholder="Buscar por proveedor..."
            style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
        </div>
        <select [(ngModel)]="filterStatus" (change)="loadInvoices()"
          style="padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; outline: none;">
          <option value="">Todas</option>
          <option value="pending">Pendientes</option>
          <option value="approved">Aprobadas</option>
          <option value="paid">Pagadas</option>
          <option value="rejected">Rechazadas</option>
        </select>
        <a [routerLink]="['/management/expenses/invoices/new']"
          style="display: flex; align-items: center; gap: 6px; padding: 8px 16px; background: #2563eb; color: white; border-radius: 8px; font-size: 13px; font-weight: 500; text-decoration: none;">
          <span class="material-symbols-outlined" style="font-size: 16px;">add</span> Nueva Factura
        </a>
      </div>

      @switch (viewState()) {
        @case ('loading') { <app-loading-state label="Cargando facturas..." /> }
        @case ('empty') { <app-empty-state icon="receipt" title="Sin facturas" description="No hay facturas registradas." /> }
        @case ('error') { <div style="text-align: center; padding: 24px; color: #dc2626;">Error al cargar facturas.</div> }
        @default {
          @if (data(); as vm) {
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
              <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead>
                  <tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                    <th style="padding: 12px 16px; text-align: left; font-weight: 600; color: #475569;">Proveedor</th>
                    <th style="padding: 12px 16px; text-align: left; font-weight: 600; color: #475569;">Categoría</th>
                    <th style="padding: 12px 16px; text-align: right; font-weight: 600; color: #475569;">Total</th>
                    <th style="padding: 12px 16px; text-align: left; font-weight: 600; color: #475569;">Estado</th>
                    <th style="padding: 12px 16px; text-align: left; font-weight: 600; color: #475569;">Fecha</th>
                    <th style="padding: 12px 16px; text-align: left; font-weight: 600; color: #475569;">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  @for (inv of vm.items; track inv.id) {
                    <tr style="border-bottom: 1px solid #f1f5f9;">
                      <td style="padding: 12px 16px; font-weight: 500; color: #0f172a;">{{ inv.vendorName }}</td>
                      <td style="padding: 12px 16px; color: #475569;">{{ inv.category }}</td>
                      <td style="padding: 12px 16px; text-align: right; font-weight: 600;">{{ inv.total | currency:'MXN':'symbol-narrow':'1.2-2' }}</td>
                      <td style="padding: 12px 16px;">
                        <span [style]="statusStyle(inv.status)">{{ statusLabel(inv.status) }}</span>
                      </td>
                      <td style="padding: 12px 16px; color: #64748b;">{{ inv.createdAt | date:'dd/MM/yyyy' }}</td>
                      <td style="padding: 12px 16px;">
                        <a [routerLink]="['/management/expenses/invoices', inv.id]" style="display: flex; align-items: center; gap: 4px; color: #2563eb; text-decoration: none; font-size: 12px;">
                          <span class="material-symbols-outlined" style="font-size: 14px;">visibility</span> Ver
                        </a>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
            @if (vm.totalPages > 1) {
              <div style="display: flex; justify-content: center; gap: 8px; margin-top: 16px; align-items: center;">
                <button (click)="goToPage(vm.page - 1)" [disabled]="!vm.hasPrev" style="padding: 6px 12px; border: 1px solid #e2e8f0; border-radius: 6px; background: white; font-size: 12px; cursor: pointer;">Anterior</button>
                <span style="font-size: 12px; color: #64748b;">Pág {{ vm.page }} de {{ vm.totalPages }}</span>
                <button (click)="goToPage(vm.page + 1)" [disabled]="!vm.hasNext" style="padding: 6px 12px; border: 1px solid #e2e8f0; border-radius: 6px; background: white; font-size: 12px; cursor: pointer;">Siguiente</button>
              </div>
            }
          }
        }
      }
    </div>
  `
})
export class InvoicesListPageComponent {
  private readonly destroyRef = inject(DestroyRef);
  private readonly api = inject(ExpensesApiService);

  readonly viewState = signal<'loading' | 'success' | 'empty' | 'error'>('loading');
  readonly data = signal<any>(null);
  readonly filterStatus = signal('');
  readonly searchVendor = signal('');
  readonly currentPage = signal(1);

  constructor() { this.loadInvoices(); }

  loadInvoices() {
    this.viewState.set('loading');
    this.api.getInvoices(this.filterStatus(), undefined, this.searchVendor(), this.currentPage())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (r) => { this.data.set(r); this.viewState.set(r.items.length ? 'success' : 'empty'); },
        error: () => this.viewState.set('error'),
      });
  }

  goToPage(p: number) { this.currentPage.set(p); this.loadInvoices(); }

  statusStyle(s: string) {
    const map: any = { pending: 'background:#fefce8;color:#a16207;', approved: 'background:#f0fdf4;color:#166534;', paid: 'background:#eff6ff;color:#1d4ed8;', rejected: 'background:#fef2f2;color:#991b1b;' };
    return map[s] || 'background:#f1f5f9;color:#475569;';
  }
  statusLabel(s: string) {
    const map: any = { pending: 'Pendiente', approved: 'Aprobada', paid: 'Pagada', rejected: 'Rechazada' };
    return map[s] || s;
  }
}
