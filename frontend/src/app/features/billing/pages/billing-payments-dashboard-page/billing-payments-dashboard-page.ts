import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { DecimalPipe } from '@angular/common';

import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { KpiChartComponent } from '../../../../shared/ui/kpi-chart/kpi-chart';
import { BillingSubNavComponent } from '../../components/billing-sub-nav/billing-sub-nav';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { BillingApiService } from '../../services/billing-api.service';
import type { PaymentDashboard } from '../../models/billing.model';

const METHOD_OPTIONS = [
  { value: '', label: 'Todos', icon: 'payments' },
  { value: 'card', label: 'Tarjeta', icon: 'credit_card' },
  { value: 'cash', label: 'Efectivo', icon: 'payments' },
  { value: 'bank_transfer', label: 'Transferencia', icon: 'account_balance' },
  { value: 'simulated', label: 'En línea', icon: 'credit_card' },
];

const STATUS_OPTIONS = [
  { value: '', label: 'Todos', icon: 'receipt_long' },
  { value: 'confirmed', label: 'Confirmados', icon: 'check_circle' },
  { value: 'refunded', label: 'Reembolsados', icon: 'currency_exchange' },
  { value: 'failed', label: 'Fallidos', icon: 'error' },
  { value: 'rejected', label: 'Rechazados', icon: 'block' },
  { value: 'no_payment', label: 'Sin pagos', icon: 'hourglass_empty' },
];

@Component({
  selector: 'app-billing-payments-dashboard-page',
  imports: [
    DecimalPipe,
    PropertySelectorComponent,
    PageHeaderComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    KpiChartComponent,
    BillingSubNavComponent,
  ],
  templateUrl: './billing-payments-dashboard-page.html',
  styleUrl: './billing-payments-dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BillingPaymentsDashboardPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly billingApi = inject(BillingApiService);
  private readonly propertyCtx = inject(PropertyContextService);

  // ── URL-driven state ──
  private readonly qp = toSignal(this.activatedRoute.queryParamMap, { initialValue: this.activatedRoute.snapshot.queryParamMap });

  readonly selectedPropId = computed(() => Number(this.qp()?.get('prop_id') ?? '0'));
  readonly selectedLabel = signal(this.activatedRoute.snapshot.queryParamMap.get('prop_label') ?? '');
  readonly currentPage = computed(() => Math.max(1, Number(this.qp()?.get('page') ?? '1')));
  readonly methodFilter = computed(() => this.qp()?.get('method') ?? '');
  readonly statusFilter = computed(() => this.qp()?.get('status') ?? '');
  readonly dateFrom = computed(() => this.qp()?.get('date_from') ?? '');
  readonly dateTo = computed(() => this.qp()?.get('date_to') ?? '');

  readonly methodOptions = METHOD_OPTIONS;
  readonly statusOptions = STATUS_OPTIONS;

  // ── Dashboard resource ──
  readonly dashboardResource = rxResource<PaymentDashboard, unknown>({
    params: () => {
      const pid = this.selectedPropId();
      return {
        propId: pid || undefined,
        page: this.currentPage(),
        method: this.methodFilter() || undefined,
        status: this.statusFilter() || undefined,
        dateFrom: this.dateFrom() || undefined,
        dateTo: this.dateTo() || undefined,
      };
    },
    stream: ({ params }) => this.billingApi.getPaymentsDashboard({
      prop_id: (params as any).propId,
      page: (params as any).page,
      method: (params as any).method,
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

  readonly hasFilters = computed(() => Boolean(this.methodFilter() || this.statusFilter() || this.dateFrom() || this.dateTo()));

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

  toggleFilter(key: 'method' | 'status', value: string, current: string): void {
    const next = value === current ? '' : value;
    this.navigate({ [key]: next || null });
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
      queryParams: { method: null, status: null, date_from: null, date_to: null, page: null },
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

  methodLabel(m: string): string {
    return ({ card: 'Tarjeta', cash: 'Efectivo', bank_transfer: 'Transferencia', simulated: 'En línea' })[m] ?? (m || 'Sin método');
  }

  methodIcon(m: string): string {
    return ({ card: 'credit_card', cash: 'payments', bank_transfer: 'account_balance', simulated: 'credit_card' })[m] ?? 'receipt';
  }

  statusLabel(s: string): string {
    return ({ confirmed: 'Confirmado', refunded: 'Reembolsado', failed: 'Fallido', rejected: 'Rechazado', no_payment: 'Sin pagos' })[s] ?? s;
  }

  statusTone(s: string): string {
    return ({ confirmed: 'success', refunded: 'warning', failed: 'danger', rejected: 'danger', no_payment: 'neutral' })[s] ?? 'neutral';
  }

  statusIcon(s: string): string {
    return ({ confirmed: 'check_circle', refunded: 'currency_exchange', failed: 'error', rejected: 'block', no_payment: 'hourglass_empty' })[s] ?? 'receipt';
  }
}
