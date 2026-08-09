import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';

import { ProductsAuthService } from '../../services/products-auth.service';
import { ProductsApiService } from '../../services/products-api.service';
import { ProductsRestockModalComponent } from '../../partials/products-restock-modal/products-restock-modal';
import type { HotelProduct, ProductType } from '../../models/products.model';
import { PRODUCT_TYPE_LABELS } from '../../models/products.model';
import type { ViewState } from '../../../../shared/types/ui-state.type';

interface TypeFilter {
  key: ProductType | 'all';
  label: string;
  count: number;
}

@Component({
  selector: 'app-products-list-page',
  imports: [
    RouterLink,
    FormsModule,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    ProductsRestockModalComponent
  ],
  templateUrl: './products-list-page.html',
  styleUrl: './products-list-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProductsListPageComponent {
  private readonly propCtx = inject(PropertyContextService);
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly productsAuth = inject(ProductsAuthService);
  private readonly productsApi = inject(ProductsApiService);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly destroyRef = inject(DestroyRef);

  readonly PRODUCT_TYPE_LABELS = PRODUCT_TYPE_LABELS;

  /** Current hotel context — drives the httpResource query. */
  readonly currentPropId = computed(() => this.propCtx.currentPropId());

  /** Permission gating: cost is manager-only. Forwarded to ProductsAuthService. */
  readonly canSeeCost = this.productsAuth.canSeeCost;
  readonly canManageCost = this.productsAuth.canManageCost;
  readonly canEdit = this.productsAuth.canEdit;
  readonly canRestock = this.productsAuth.canRestock;
  readonly canCreate = this.productsAuth.canCreate;

  /** Search and filter state. */
  readonly searchTerm = signal('');
  readonly typeFilter = signal<ProductType | 'all'>('all');

  /** Restock modal state. */
  readonly restockProduct = signal<HotelProduct | null>(null);
  readonly showRestockModal = signal(false);

  /** Products resource (Angular 22 httpResource). The parsed response keeps
   *  the raw envelope `{ items: [...] }`; the `products` computed below
   *  unwraps + maps each DTO into a domain HotelProduct. */
  readonly productsResource = httpResource<{ items: any[] }>(() => {
    const pid = this.currentPropId();
    return pid ? `/management/products/hotels/${pid}` : undefined;
  });

  /** Map the raw response to domain `HotelProduct[]`. */
  readonly products = computed<HotelProduct[]>(() => {
    const raw = this.productsResource.value();
    if (!raw) return [];
    const items = Array.isArray(raw) ? raw : (raw.items ?? []);
    return items.map((dto: any) => ({
      productId: dto.product_id,
      propId: dto.prop_id,
      name: dto.name,
      description: dto.description ?? '',
      category: dto.category ?? 'Otros',
      type: (dto.type ?? 'retail') as ProductType,
      costPrice: dto.cost_price ?? 0,
      unitPrice: dto.unit_price ?? 0,
      quantityAvailable: dto.quantity_available ?? 0,
      defaultSupplier: dto.default_supplier ?? null,
      supplierSku: dto.supplier_sku ?? null,
      parLevel: dto.par_level ?? null,
      lastPurchaseInvoiceRef: dto.last_purchase_invoice_ref ?? null,
      lastPurchaseInvoice: dto.last_purchase_invoice
        ? {
            id: dto.last_purchase_invoice.id,
            vendorName: dto.last_purchase_invoice.vendor_name,
            invoiceDate: dto.last_purchase_invoice.invoice_date,
            dueDate: dto.last_purchase_invoice.due_date,
            total: dto.last_purchase_invoice.total,
            status: dto.last_purchase_invoice.status,
          }
        : null,
      lastPurchaseQty: dto.last_purchase_qty ?? null,
      lastPurchaseAt: dto.last_purchase_at ?? null,
      isActive: dto.is_active ?? true,
      archivedAt: dto.archived_at ?? null,
      archivedBy: dto.archived_by ?? null,
      createdAt: dto.created_at,
      updatedAt: dto.updated_at,
    }));
  });

  readonly filteredProducts = computed(() => {
    const term = this.searchTerm().trim().toLowerCase();
    const type = this.typeFilter();
    return this.products().filter((p) => {
      if (type !== 'all' && p.type !== type) return false;
      if (term) {
        const haystack = `${p.name} ${p.category} ${p.productId}`.toLowerCase();
        if (!haystack.includes(term)) return false;
      }
      return true;
    });
  });

  /** Type chip counts. */
  readonly typeFilters = computed<TypeFilter[]>(() => {
    const products = this.products();
    const counts: Record<ProductType | 'all', number> = {
      all: products.length,
      retail: products.filter((p) => p.type === 'retail').length,
      supply: products.filter((p) => p.type === 'supply').length,
      asset: products.filter((p) => p.type === 'asset').length,
    };
    return [
      { key: 'all', label: 'Todos', count: counts.all },
      { key: 'retail', label: 'Retail', count: counts.retail },
      { key: 'supply', label: 'Suministros', count: counts.supply },
      { key: 'asset', label: 'Activos', count: counts.asset },
    ];
  });

  /** View state (loading / error / success / empty). */
  readonly viewState = computed<ViewState>(() => {
    if (this.productsResource.isLoading()) return 'loading';
    const err = this.productsResource.error();
    if (err) return 'error';
    const list = this.products();
    return list.length > 0 ? 'success' : 'empty';
  });

  reload(): void {
    this.productsResource.reload();
  }

  onSearchInput(value: string): void {
    this.searchTerm.set(value);
  }

  onTypeChange(type: ProductType | 'all'): void {
    this.typeFilter.set(type);
  }

  /** Compute margin (unit_price - cost_price). Manager-only via template guard. */
  margin(p: HotelProduct): number {
    return p.unitPrice - p.costPrice;
  }

  /** Compute margin %. */
  marginPct(p: HotelProduct): number {
    if (p.unitPrice <= 0) return 0;
    return ((p.unitPrice - p.costPrice) / p.unitPrice) * 100;
  }

  /** Status badge. */
  statusLabel(p: HotelProduct): string {
    if (p.archivedAt) return 'Archivado';
    return p.isActive ? 'Activo' : 'Inactivo';
  }
  statusClass(p: HotelProduct): string {
    if (p.archivedAt) return 'status-archived';
    return p.isActive ? 'status-active' : 'status-inactive';
  }

  openRestock(p: HotelProduct): void {
    this.restockProduct.set(p);
    this.showRestockModal.set(true);
  }

  closeRestock(): void {
    this.showRestockModal.set(false);
    this.restockProduct.set(null);
  }

  onRestockSuccess(): void {
    this.closeRestock();
    this.reload();
  }

  edit(p: HotelProduct): void {
    const pid = this.currentPropId();
    if (!pid) return;
    this.router.navigate(['/management/products', p.productId, 'edit'], {
      queryParams: { prop_id: pid }
    });
  }

  create(): void {
    const pid = this.currentPropId();
    if (!pid) return;
    this.router.navigate(['/management/products', 'new'], {
      queryParams: { prop_id: pid }
    });
  }

  async toggleActive(p: HotelProduct): Promise<void> {
    const pid = this.currentPropId();
    if (!pid) return;
    const action = p.isActive ? 'desactivar' : 'activar';
    const ok = await this.confirmDialog.open({
      title: `${action.charAt(0).toUpperCase() + action.slice(1)} producto`,
      message: `¿${action.charAt(0).toUpperCase() + action.slice(1)} "${p.name}"?`,
      confirmLabel: action.charAt(0).toUpperCase() + action.slice(1),
      variant: p.isActive ? 'danger' : 'default',
    });
    if (!ok) return;
    this.productsApi
      .updateHotelProduct(pid, p.productId, { is_active: !p.isActive })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => this.reload(),
        error: () => { /* swallow; resource reload keeps current view */ },
      });
  }

  trackByProductId(_index: number, p: HotelProduct): string {
    return p.productId;
  }
}