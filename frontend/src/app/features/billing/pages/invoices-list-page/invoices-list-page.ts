import { CurrencyPipe, DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { InvoiceStatsDto } from '../../models/billing.dto';
import { BillingApiService } from '../../services/billing-api.service';

@Component({
  selector: 'app-invoices-list-page',
  imports: [CurrencyPipe, DatePipe, RouterLink, FormsModule, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent],
  templateUrl: './invoices-list-page.html',
  styleUrl: './invoices-list-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InvoicesListPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly billingApi = inject(BillingApiService);
  private readonly router = inject(Router);

  // ── URL-driven state ──
  private readonly qp = toSignal(this.activatedRoute.queryParamMap, { initialValue: this.activatedRoute.snapshot.queryParamMap });

  readonly currentPage = computed(() => Math.max(1, Number(this.qp()?.get('page') ?? '1')));
  readonly statusFilter = computed(() => this.qp()?.get('status') ?? '');
  readonly searchQuery = computed(() => this.qp()?.get('q') ?? '');
  readonly dateFrom = computed(() => this.qp()?.get('date_from') ?? '');
  readonly dateTo = computed(() => this.qp()?.get('date_to') ?? '');

  // ── Stats resource ──
  readonly statsResource = rxResource<InvoiceStatsDto, undefined>({
    loader: () => this.billingApi.getInvoiceStats(),
  });

  readonly stats = computed(() => this.statsResource.value());

  // ── Invoices resource ──
  readonly invoicesResource = rxResource({
    request: () => ({
      page: this.currentPage(),
      status: this.statusFilter() || undefined,
      q: this.searchQuery() || undefined,
      dateFrom: this.dateFrom() || undefined,
      dateTo: this.dateTo() || undefined,
    }),
    loader: ({ request }) => this.billingApi.getInvoices(request.page, {
      status: request.status,
      q: request.q,
      date_from: request.dateFrom,
      date_to: request.dateTo,
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
    return c;
  });

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

  clearAllFilters(): void {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { status: null, q: null, date_from: null, date_to: null, page: null },
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
