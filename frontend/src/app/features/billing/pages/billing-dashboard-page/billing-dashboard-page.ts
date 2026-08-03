import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { DecimalPipe } from '@angular/common';

import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { KpiChartComponent } from '../../../../shared/ui/kpi-chart/kpi-chart';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { BillingApiService } from '../../services/billing-api.service';
import type { InvoiceDashboard } from '../../models/billing.model';

const STATUS_OPTIONS = [
  { value: '', label: 'Todos', icon: 'receipt_long' },
  { value: 'issued', label: 'Emitidas', icon: 'receipt_long' },
  { value: 'paid', label: 'Pagadas', icon: 'check_circle' },
  { value: 'cancelled', label: 'Anuladas', icon: 'cancel' },
  { value: 'refunded', label: 'Reembolsadas', icon: 'currency_exchange' },
];

@Component({
  selector: 'app-billing-dashboard-page',
  imports: [
    RouterLink,
    DecimalPipe,
    PropertySelectorComponent,
    PageHeaderComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    KpiChartComponent,
  ],
  templateUrl: './billing-dashboard-page.html',
  styleUrl: './billing-dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BillingDashboardPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly billingApi = inject(BillingApiService);
  private readonly propertyCtx = inject(PropertyContextService);

  // ── URL-driven state ──
  private readonly qp = toSignal(this.activatedRoute.queryParamMap, { initialValue: this.activatedRoute.snapshot.queryParamMap });

  readonly selectedPropId = computed(() => Number(this.qp()?.get('prop_id') ?? '0'));
  readonly selectedLabel = signal(this.activatedRoute.snapshot.queryParamMap.get('prop_label') ?? '');
  readonly currentPage = computed(() => Math.max(1, Number(this.qp()?.get('page') ?? '1')));
  readonly statusFilter = computed(() => this.qp()?.get('status') ?? '');
  readonly dateFrom = computed(() => this.qp()?.get('date_from') ?? '');
  readonly dateTo = computed(() => this.qp()?.get('date_to') ?? '');

  readonly statusOptions = STATUS_OPTIONS;

  // ── Dashboard resource ──
  readonly dashboardResource = rxResource<InvoiceDashboard, unknown>({
    params: () => {
      const pid = this.selectedPropId();
      return {
        propId: pid || undefined,
        page: this.currentPage(),
        status: this.statusFilter() || undefined,
        dateFrom: this.dateFrom() || undefined,
        dateTo: this.dateTo() || undefined,
      };
    },
    stream: ({ params }) => this.billingApi.getInvoiceDashboard({
      prop_id: (params as any).propId,
      page: (params as any).page,
      status: (params as any).status,
      date_from: (params as any).dateFrom,
      date_to: (params as any).dateTo,
    }),
  });

  readonly data = computed(() => this.dashboardResource.value() ?? null);
  readonly summary = computed(() => this.data()?.summary ?? null);
  readonly series = computed(() => this.data()?.series ?? { labels: [], datasets: [] });
  readonly rows = computed(() => this.data()?.rows ?? []);

  readonly viewState = computed<ViewState>(() => {
    const r = this.dashboardResource;
    if (r.isLoading()) return 'loading';
    if (r.error()) return 'error';
    if (!r.value()) return 'empty';
    return 'success';
  });

  readonly chartDatasets = computed(() => this.series().datasets.map(ds => ({ label: ds.label, data: ds.data })));

  /** Preset activo según el rango de fechas de la URL (7/30/90 días). */
  readonly activeRange = computed<'7' | '30' | '90' | null>(() => {
    const from = this.dateFrom();
    const to = this.dateTo();
    if (!from || !to) return null;
    const start = new Date(`${from}T00:00:00`);
    const end = new Date(`${to}T00:00:00`);
    const diff = Math.round((end.getTime() - start.getTime()) / 86_400_000) + 1;
    return diff === 7 ? '7' : diff === 30 ? '30' : diff === 90 ? '90' : null;
  });

  // ── Helpers ──

  onPropSelected(event: { propId: number; label: string }): void {
    const label = event.label || `Propiedad #${event.propId}`;
    this.selectedLabel.set(label);
    if (event.propId) {
      this.propertyCtx.setProperty(event.propId, label);
    } else {
      this.propertyCtx.clear();
    }
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { prop_id: event.propId || null, prop_label: label || null, page: null },
      queryParamsHandling: 'merge',
    });
  }

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

  /** Quick period presets: 7, 30, 90 days ending today. */
  setRange(days: number): void {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - (days - 1));
    const fmt = (d: Date) => d.toISOString().slice(0, 10);
    this.navigate({ date_from: fmt(start), date_to: fmt(end) });
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
      queryParams: { status: null, date_from: null, date_to: null, page: null },
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

  formatDate(val: string): string {
    if (!val) return '—';
    const d = new Date(`${val}T00:00:00`);
    if (isNaN(d.getTime())) return val;
    return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  statusLabel(s: string): string {
    return ({ issued: 'Emitida', paid: 'Pagada', cancelled: 'Anulada', refunded: 'Reembolsada' })[s] ?? s;
  }

  statusTone(s: string): string {
    return ({ issued: 'warning', paid: 'success', cancelled: 'danger', refunded: 'danger' })[s] ?? 'neutral';
  }

  statusIcon(s: string): string {
    return ({ issued: 'receipt_long', paid: 'check_circle', cancelled: 'cancel', refunded: 'currency_exchange' })[s] ?? 'receipt';
  }
}
