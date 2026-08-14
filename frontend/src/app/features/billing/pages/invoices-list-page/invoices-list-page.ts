import { ChangeDetectionStrategy, Component, computed, inject, OnInit, signal } from '@angular/core';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { of } from 'rxjs';

import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { ToastService } from '../../../../shared/services/toast.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { InvoiceStatsDto } from '../../models/billing.dto';
import type { InvoiceListItem } from '../../models/billing.model';
import type { ApiError } from '../../../../core/api/api-error.model';
import { AuthService } from '../../../../core/auth/auth.service';
import { type PermissionCode } from '../../../../core/auth/permission.constants';
import { BillingApiService } from '../../services/billing-api.service';

@Component({
  selector: 'app-invoices-list-page',
  imports: [RouterLink, FormsModule, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, PropertySelectorComponent],
  templateUrl: './invoices-list-page.html',
  styleUrl: './invoices-list-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InvoicesListPageComponent implements OnInit {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly billingApi = inject(BillingApiService);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly auth = inject(AuthService);

  readonly cancellingId = signal<string | null>(null);
  readonly canManageInvoices = computed(() => this.auth.hasPermission('billing.manage' as PermissionCode));

  // ── URL-driven state ──
  private readonly qp = toSignal(this.activatedRoute.queryParamMap, { initialValue: this.activatedRoute.snapshot.queryParamMap });

  readonly selectedPropId = computed(() => Number(this.qp()?.get('prop_id') ?? '0'));
  readonly selectedLabel = signal(this.activatedRoute.snapshot.queryParamMap.get('prop_label') ?? '');
  readonly currentPage = computed(() => Math.max(1, Number(this.qp()?.get('page') ?? '1')));
  readonly statusFilter = computed(() => this.qp()?.get('status') ?? '');
  readonly searchQuery = computed(() => this.qp()?.get('q') ?? '');
  readonly dateFrom = computed(() => this.qp()?.get('date_from') ?? '');
  readonly dateTo = computed(() => this.qp()?.get('date_to') ?? '');
  readonly turnoFilter = computed(() => this.qp()?.get('turno') ?? '');
  readonly cajeroFilter = computed(() => this.qp()?.get('cajero') ?? '');

  /** Turnos del hotel para el filtro (degrada a vacío sin shifts.read). */
  readonly shiftOptions = signal<{ id: string; label: string }[]>([]);

  // ── Stats resource ──
  readonly statsResource = rxResource<InvoiceStatsDto | undefined, number | undefined>({
    params: () => this.selectedPropId() || undefined,
    stream: ({ params }) => params ? this.billingApi.getInvoiceStats(params) : of<InvoiceStatsDto | undefined>(undefined),
  });

  readonly stats = computed(() => this.statsResource.value());

  // ── Invoices resource ──
  readonly invoicesResource = rxResource<any, any>({
    params: () => {
      const pid = this.selectedPropId();
      return {
        propId: pid || undefined,
        page: this.currentPage(),
        status: this.statusFilter() || undefined,
        q: this.searchQuery() || undefined,
        dateFrom: this.dateFrom() || undefined,
        dateTo: this.dateTo() || undefined,
        turno: this.turnoFilter() || undefined,
        cajero: this.cajeroFilter() || undefined,
      };
    },
    stream: ({ params }) => this.billingApi.getInvoices((params as any).page, {
      prop_id: (params as any).propId,
      status: (params as any).status,
      q: (params as any).q,
      date_from: (params as any).dateFrom,
      date_to: (params as any).dateTo,
      turno: (params as any).turno,
      cajero: (params as any).cajero,
    }),
  });

  readonly viewState = computed<ViewState>(() => {
    const r = this.invoicesResource;
    if (r.isLoading()) return 'loading';
    if (r.error()) return 'error';
    if (!r.value()?.items.length) return 'empty';
    return 'success';
  });

  // ── UI state ──
  readonly dateFromInput = signal('');
  readonly dateToInput = signal('');

  readonly activeFilterCount = computed(() => {
    let c = 0;
    if (this.statusFilter()) c++;
    if (this.searchQuery()) c++;
    if (this.dateFrom() || this.dateTo()) c++;
    if (this.turnoFilter()) c++;
    if (this.cajeroFilter()) c++;
    return c;
  });

  /** Carga las opciones de turno del hotel seleccionado para el filtro. */
  private loadShiftOptions(propId: number): void {
    if (!propId) {
      this.shiftOptions.set([]);
      return;
    }
    this.billingApi.getShiftOptions(propId).subscribe({
      next: (options) => this.shiftOptions.set(options),
      error: () => this.shiftOptions.set([]),
    });
  }

  ngOnInit(): void {
    this.loadShiftOptions(this.selectedPropId());
  }

  // ── Property selection ──
  onPropSelected(event: { propId: number; label: string }): void {
    const label = event.label || `Propiedad #${event.propId}`;
    this.selectedLabel.set(label);
    if (event.propId) {
      this.propertyCtx.setProperty(event.propId, label);
    } else {
      this.propertyCtx.clear();
    }
    this.loadShiftOptions(event.propId);
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { prop_id: event.propId || null, prop_label: label || null, page: null },
      queryParamsHandling: 'merge',
    });
  }

  // ── Navigation helpers ──

  private navigate(params: Record<string, string | null>): void {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { page: null, ...params },
      queryParamsHandling: 'merge',
    });
  }

  setStatusFilter(status: string): void {
    const next = status === this.statusFilter() ? '' : status;
    this.navigate({ status: next || null });
  }

  onSearch(value: string): void {
    this.navigate({ q: value || null });
  }

  onDateFromChange(value: string): void {
    this.navigate({ date_from: value || null });
  }

  onDateToChange(value: string): void {
    this.navigate({ date_to: value || null });
  }

  setTurnoFilter(id: string): void {
    const next = id === this.turnoFilter() ? '' : id;
    this.navigate({ turno: next || null });
  }

  setCajeroFilter(value: string): void {
    this.navigate({ cajero: value || null });
  }

  clearAllFilters(): void {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { status: null, q: null, date_from: null, date_to: null, turno: null, cajero: null, page: null },
      queryParamsHandling: 'merge',
    });
  }

  goToPage(page: number): void {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { page: page > 1 ? page : null },
      queryParamsHandling: 'merge',
    });
  }

  // ── Actions ──

  /** Solo las facturas emitidas pueden anularse (state machine: issued → cancelled). */
  canCancel(item: InvoiceListItem): boolean {
    return item?.status === 'issued' && this.canManageInvoices();
  }

  async cancelInvoice(item: InvoiceListItem): Promise<void> {
    const reason = await this.confirmDialog.openPrompt({
      title: 'Anular factura',
      message: '¿Anular esta factura? Esta acción no se puede deshacer.',
      confirmLabel: 'Anular factura',
      variant: 'danger',
      mode: 'delete',
      modeDetail: item.invoiceNumber || item.id,
      input: {
        label: 'Motivo de la anulación (opcional)',
        placeholder: 'Ej. Factura duplicada, error en el cobro…',
        maxLength: 500,
      },
    });
    if (reason === null) return;
    this.cancellingId.set(item.id);
    this.billingApi.cancelInvoice(item.id, this.selectedPropId(), reason)
      .subscribe({
        next: () => {
          this.toast.show('Factura anulada correctamente.', 'info', 4000);
          this.cancellingId.set(null);
          this.invoicesResource.reload();
          this.statsResource.reload();
        },
        error: (err: ApiError) => {
          this.toast.show(err.message || 'Error al anular la factura.', 'error', 5000);
          this.cancellingId.set(null);
        },
      });
  }

  // ── Helpers ──

  statusLabel(s: string): string {
    return (
      { issued: 'Emitida', paid: 'Pagada', cancelled: 'Anulada', refunded: 'Reembolsada' }[s]
    ) ?? s;
  }

  statusTone(s: string): string {
    return (
      { issued: 'warning', paid: 'success', cancelled: 'danger', refunded: 'danger' }[s]
    ) ?? 'neutral';
  }

  formatDate(val: string): string {
    if (!val) return '—';
    const d = new Date(val);
    if (isNaN(d.getTime())) return val.slice(0, 10);
    return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  statusIcon(s: string): string {
    return (
      { issued: 'receipt_long', paid: 'check_circle', cancelled: 'cancel', refunded: 'currency_exchange' }[s]
    ) ?? 'receipt';
  }
}
