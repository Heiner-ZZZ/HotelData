import { CurrencyPipe, DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';

import { getErrorStatus } from '../../../../shared/utils/http-error.util';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ExpensesApiService } from '../../services/expenses-api.service';
import type { InvoiceProductLine } from '../../models/expenses.model';

@Component({
  selector: 'app-invoice-detail-page',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, PageHeaderComponent, LoadingStateComponent],
  styleUrl: '../../expenses.shared.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page-wrap page-wrap--narrow">
      <app-page-header eyebrow="Vendor AP · Gastos" title="Detalle de factura de proveedor" description="Documento de cuentas por pagar del hotel y su trazabilidad operativa." />

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

              @if (i.status === 'paid' && i.payment_reference) {
                <div class="meta-tile meta-tile--full">
                  <h4 class="meta-tile__heading">Trazabilidad del pago</h4>
                  <div class="meta-row">
                    <div><span class="meta-row__label">Método:</span> <span class="meta-row__value">{{ i.payment_method || '—' }}</span></div>
                    <div><span class="meta-row__label">Referencia:</span> <span class="meta-row__value">{{ i.payment_reference }}</span></div>
                    <div><span class="meta-row__label">Asiento:</span> <span class="meta-row__value">{{ i.payment_journal_id || '—' }}</span></div>
                  </div>
                </div>
              }

              <!-- Linked restocks (reverse view) -->
              @if (i.productLines?.length) {
                <div class="meta-tile meta-tile--full">
                  <div class="meta-tile__head-row">
                    <h4 class="meta-tile__heading">Restocks vinculados</h4>
                    <button
                      class="btn btn--sm btn--outline"
                      type="button"
                      (click)="goToInventory()"
                      [title]="i.prop_id ? ('Ver el inventario de la propiedad ' + i.prop_id) : 'Ver el inventario'"
                    >
                      <span class="material-symbols-outlined icon">inventory_2</span>
                      Ir al inventario
                    </button>
                  </div>
                  <p class="meta-tile__hint">
                    Productos repuestos con esta factura — el stock y costo son los actuales.
                  </p>
                  @for (line of i.productLines; track line.productId) {
                  <div class="restock-line">
                    <a class="restock-line__name" [href]="productHref(line)" (click)="openProduct($event, line)">
                      <span class="material-symbols-outlined restock-line__icon">inventory_2</span>
                      {{ line.name }}
                      @if (!line.restocked) {
                        <span class="restock-line__fail">
                          <span class="material-symbols-outlined">warning</span> falló
                        </span>
                      }
                    </a>
                    <span class="restock-line__qty">{{ line.qty }} uds × {{ line.unitCost | currency:'MXN':'symbol-narrow' }} = {{ line.lineTotal | currency:'MXN':'symbol-narrow' }}</span>
                    <span class="restock-line__stock" [class.restock-line__stock--muted]="line.stockNow == null">
                      <span class="material-symbols-outlined">inventory</span>
                      Stock actual: {{ line.stockNow == null ? '—' : line.stockNow }}
                    </span>
                  </div>
                  }
                </div>
              }

              <!-- Actions -->
              @if (i.status === 'pending') {
                <div class="meta-actions">
                  <button class="btn btn--lg btn--ghost-danger" type="button" (click)="updateStatus(i.id, 'rejected')">Rechazar</button>
                  <button class="btn btn--lg btn--success" type="button" (click)="updateStatus(i.id, 'approved')">Aprobar</button>
                </div>
              }
              @if (i.status === 'approved') {
                <div class="meta-actions">
                  <button class="btn btn--lg btn--primary" type="button" (click)="payInvoice(i.id)">Registrar pago por transferencia</button>
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
  private readonly propertyContext = inject(PropertyContextService);

  // ── Reactive route param — httpResource re-fires when this changes ──
  private readonly paramMap = toSignal(this.route.paramMap, {
    initialValue: this.route.snapshot.paramMap,
  });
  readonly invId = computed(() => this.paramMap().get('invoiceId') ?? '');

  readonly detailResource = httpResource<any>(() => {
    const id = this.invId();
    const propId = this.propertyContext.currentPropId();
    return id && propId > 0
      ? `/api/hotels/${propId}/vendor-ap/invoices/${id}`
      : undefined;
  });

  readonly inv = computed(() => {
    // value() LANZA cuando el request falló — leer error() antes para degradar
    // con gracia (404 → 'empty', otros → 'error') sin romper el template.
    if (this.detailResource.error()) return null;
    const raw = this.detailResource.value();
    if (!raw) return null;
    return {
      ...raw,
      // camelCase mirror so the template can render the reverse view; the
      // API (InvoiceResponse, extra="allow") sends snake_case product_lines.
      // KEEP IN SYNC with the line mapping in mapInvoiceDetail (expenses.mapper.ts).
      productLines: (raw.product_lines ?? []).map((l: any) => ({
        productId: l.product_id,
        name: l.name ?? l.product_id,
        qty: l.qty ?? 0,
        unitCost: l.unit_cost ?? 0,
        lineTotal: l.line_total ?? 0,
        restocked: l.restocked !== false,
        stockNow: l.stock_now ?? null,
        costNow: l.cost_now ?? null,
      })),
    };
  });

  /** Reverse view: the products restocked by this invoice, with live stock. */
  readonly productLines = computed<InvoiceProductLine[]>(() => this.inv()?.productLines ?? []);

  readonly viewState = computed<'loading' | 'success' | 'error' | 'empty'>(() => {
    // error() ANTES de value(): value() lanza cuando el request falló.
    const err = this.detailResource.error();
    if (err) return getErrorStatus(err) === 404 ? 'empty' : 'error';
    const v = this.detailResource.value();
    // Anti-flicker: keep 'success' during silent reloads after mutations
    // (updateStatus() → detailResource.reload() triggers a brief isLoading).
    if (this.detailResource.isLoading() && !v) return 'loading';
    return v ? 'success' : 'loading';
  });

  goBack() { this.router.navigate(['/management/expenses/invoices']); }

  productHref(line: InvoiceProductLine): string {
    const pid = this.inv()?.prop_id;
    return `/management/products/${line.productId}/edit${pid ? `?prop_id=${pid}` : ''}`;
  }

  /**
   * Jump to the product list filtered by THIS invoice's hotel, keeping the
   * property context (the products list page reads prop_id from the query
   * param via PropertyContextService).
   */
  goToInventory(): void {
    const pid = this.inv()?.prop_id;
    void this.router.navigate(['/management/products'], {
      queryParams: pid ? { prop_id: pid } : {},
    });
  }

  openProduct(event: Event, line: InvoiceProductLine): void {
    event.preventDefault();
    void this.router.navigate(['/management/products', line.productId, 'edit'], {
      queryParams: this.inv()?.prop_id ? { prop_id: this.inv()?.prop_id } : {},
    });
  }

  updateStatus(id: string, status: string) {
    // Server-side update; httpResource reload picks up the new value and
    // re-renders the template via `inv()` (computed).
    this.api.updateInvoice(id, { status }, this.propertyContext.currentPropId()).subscribe({
      next: () => { this.detailResource.reload(); },
    });
  }

  payInvoice(id: string): void {
    this.api.payInvoice(id, this.propertyContext.currentPropId()).subscribe({
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
