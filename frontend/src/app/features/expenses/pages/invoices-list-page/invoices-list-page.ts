import { CurrencyPipe, DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';

import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ExpensesApiService } from '../../services/expenses-api.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';

@Component({
  selector: 'app-invoices-list-page',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, RouterLink, FormsModule, PageHeaderComponent, LoadingStateComponent, EmptyStateComponent],
  styleUrl: '../../expenses.shared.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page-wrap">
      <app-page-header eyebrow="Gastos" title="Facturas y Compras" description="Registro de facturas, aprobaciones y pagos." />

      <div class="filter-bar">
        <div class="grow">
          <input class="field-input" type="text" [(ngModel)]="searchVendor" (input)="loadInvoices()" placeholder="Buscar por proveedor..." />
        </div>
        <select class="field-select" style="width: auto;" [(ngModel)]="filterStatus" (change)="loadInvoices()">
          <option value="">Todas</option>
          <option value="pending">Pendientes</option>
          <option value="approved">Aprobadas</option>
          <option value="paid">Pagadas</option>
          <option value="rejected">Rechazadas</option>
        </select>
        <a class="btn btn--primary" [routerLink]="['/management/expenses/invoices/new']">
          <span class="material-symbols-outlined icon">add</span> Nueva Factura
        </a>
      </div>

      @switch (viewState()) {
        @case ('loading') { <app-loading-state label="Cargando facturas..." /> }
        @case ('empty') { <app-empty-state icon="receipt" title="Sin facturas" description="No hay facturas registradas." /> }
        @case ('error') { <div class="error-line">Error al cargar facturas.</div> }
        @default {
          @if (data(); as vm) {
            <div class="data-card">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Proveedor</th>
                    <th>Categoría</th>
                    <th>Total</th>
                    <th>Estado</th>
                    <th>Fecha</th>
                    <th>Acción</th>
                  </tr>
                </thead>
                <tbody>
                  @for (inv of vm.items; track inv.id) {
                    <tr>
                      <td style="font-weight: 500;">{{ inv.vendorName }}</td>
                      <td>{{ inv.category }}</td>
                      <td class="right">{{ inv.total | currency:'MXN':'symbol-narrow':'1.2-2' }}</td>
                      <td>
                        <span [class]="'badge badge--' + (inv.status || 'default')">{{ statusLabel(inv.status) }}</span>
                      </td>
                      <td style="color: var(--muted-text);">{{ inv.createdAt | date:'dd/MM/yyyy' }}</td>
                      <td>
                        <a class="view-link" [routerLink]="['/management/expenses/invoices', inv.id]">
                          <span class="material-symbols-outlined icon">visibility</span> Ver
                        </a>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
            @if (vm.totalPages > 1) {
              <div class="pagination">
                <button class="btn btn--sm" type="button" (click)="goToPage(vm.page - 1)" [disabled]="!vm.hasPrev">Anterior</button>
                <span class="pagination__info">Pág {{ vm.page }} de {{ vm.totalPages }}</span>
                <button class="btn btn--sm" type="button" (click)="goToPage(vm.page + 1)" [disabled]="!vm.hasNext">Siguiente</button>
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
  private readonly propertyContext = inject(PropertyContextService);

  readonly viewState = signal<'loading' | 'success' | 'empty' | 'error'>('loading');
  readonly data = signal<any>(null);
  readonly filterStatus = signal('');
  readonly searchVendor = signal('');
  readonly currentPage = signal(1);

  constructor() { this.loadInvoices(); }

  loadInvoices() {
    this.viewState.set('loading');
    this.api.getInvoices(
      this.filterStatus(), undefined, this.searchVendor(), this.currentPage(),
      this.propertyContext.currentPropId() || undefined,
    )
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (r) => { this.data.set(r); this.viewState.set(r.items.length ? 'success' : 'empty'); },
        error: () => this.viewState.set('error'),
      });
  }

  goToPage(p: number) { this.currentPage.set(p); this.loadInvoices(); }

  statusLabel(s: string) {
    const map: any = { pending: 'Pendiente', approved: 'Aprobada', paid: 'Pagada', rejected: 'Rechazada' };
    return map[s] || s;
  }
}
