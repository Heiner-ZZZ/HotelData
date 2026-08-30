import { CurrencyPipe, DatePipe, DecimalPipe } from '@angular/common';
import { httpResource, HttpResourceRef, HttpResourceRequest } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ProductsAuthService } from '../../services/products-auth.service';
import { ReportApiService } from '../../services/report-api.service';
import { ProductsSectionNavComponent } from '../products-section-nav/products-section-nav';
import {
  COGS_METHODS,
  type CogsMethod,
  type CogsReportDto,
  type LayerBreakdownDto,
  type StockValueReportPeriod,
} from '../../models/products-report.dto';

const PERIOD_OPTIONS: { key: StockValueReportPeriod; label: string }[] = [
  { key: 'week', label: 'Semana' },
  { key: 'month', label: 'Mes' },
  { key: 'year', label: 'Año' },
  { key: 'all', label: 'Todo' },
];

@Component({
  selector: 'app-cogs-report',
  standalone: true,
  imports: [
    CurrencyPipe,
    DatePipe,
    DecimalPipe,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    ProductsSectionNavComponent,
  ],
  templateUrl: './cogs-report.html',
  styleUrl: './cogs-report.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export default class CogsReportComponent {
  private readonly api = inject(ReportApiService);
  private readonly propCtx = inject(PropertyContextService);
  private readonly productsAuth = inject(ProductsAuthService);

  readonly propId = computed(() => this.propCtx.currentPropId());
  readonly period = signal<StockValueReportPeriod>('month');
  // Fase 6: drain method selector. Default aligns with GAAP ("First-in,
  // first-out" matches what auditors expect on a balance sheet).
  readonly method = signal<CogsMethod>('fifo');

  readonly PERIOD_OPTIONS = PERIOD_OPTIONS;
  readonly COGS_METHODS = COGS_METHODS;

  readonly canSeeCost = this.productsAuth.canSeeCost;

  readonly report: HttpResourceRef<CogsReportDto | undefined>;

  constructor() {
    // httpResource is a Signal: re-derives whenever period OR method changes.
    // The backend resolves the same URL pattern with a different cost flow.
    this.report = httpResource<CogsReportDto>(() => {
      // undefined → el httpResource NO dispara (un url '' pegaría a /api raíz → 404).
      const url = this.api.cogsReportUrl(this.propId, this.period, this.method);
      return url ? { url } : undefined;
    });
  }

  selectPeriod(p: StockValueReportPeriod): void {
    this.period.set(p);
  }

  selectMethod(m: CogsMethod): void {
    this.method.set(m);
  }

  periodLabel(p: StockValueReportPeriod): string {
    return PERIOD_OPTIONS.find((o) => o.key === p)?.label ?? p;
  }

  methodLabel(m: CogsMethod): string {
    return COGS_METHODS.find((o) => o.key === m)?.label ?? m;
  }

  formatPct(value: number, total: number): string {
    if (total === 0) return '—';
    return `${((value / total) * 100).toFixed(1)}%`;
  }

  /** Compute each item's share of the total COGS as a 0-100 bar width. */
  itemSharePct(cogs: number, total: number): number {
    if (total === 0) return 0;
    return Math.round((cogs / total) * 100);
  }

  /**
   * Defensive helper for templates: returns safe fallback when layer_breakdown
   * is missing (e.g. method=approx returns a precise shape, but Fase 5 cached
   * responses could lack it during a cache-flush window).
   */
  layersFor(item: CogsReportDto['items'][number]): LayerBreakdownDto[] {
    return item.layer_breakdown ?? [];
  }

  /** Tag for layer_breakdown: human-readable label for the op status. */
  layerSourceTag(source: string): string {
    if (source === 'layer') return 'Capa';
    if (source === 'approx_fallback') return 'Aprox.';
    if (source === 'fallback_layer_missing') return 'Sin capa';
    return source;
  }
}
