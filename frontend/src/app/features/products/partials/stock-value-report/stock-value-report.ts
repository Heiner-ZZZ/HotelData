import { CurrencyPipe, DecimalPipe, DatePipe } from '@angular/common';
import { httpResource, HttpResourceRef } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { BaseChartDirective, provideCharts, withDefaultRegisterables } from 'ng2-charts';
import type { ChartConfiguration, ChartData } from 'chart.js';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ProductsAuthService } from '../../services/products-auth.service';
import { ReportApiService } from '../../services/report-api.service';
import { ProductsSectionNavComponent } from '../products-section-nav/products-section-nav';
import { KpiChartComponent } from '../../../../shared/ui/kpi-chart/kpi-chart';
import type { StockValueItemDto, StockValueReportDto } from '../../models/products-report.dto';
import { ThemeService } from '../../../../core/theme/theme.service';

@Component({
  selector: 'app-stock-value-report',
  standalone: true,
  imports: [
    CurrencyPipe,
    DecimalPipe,
    DatePipe,
    FormsModule,
    BaseChartDirective,
    KpiChartComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    ProductsSectionNavComponent,
  ],
  providers: [provideCharts(withDefaultRegisterables())],
  templateUrl: './stock-value-report.html',
  styleUrl: './stock-value-report.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export default class StockValueReportComponent {
  private readonly api = inject(ReportApiService);
  private readonly propCtx = inject(PropertyContextService);
  private readonly productsAuth = inject(ProductsAuthService);
  private readonly themeService = inject(ThemeService);

  readonly propId = computed(() => this.propCtx.currentPropId());
  readonly searchTerm = signal('');
  readonly chartMode = signal<'line' | 'donut'>('line');

  readonly asOfEyebrow = computed<string>(() => {
    const data = this.report.value();
    if (!data?.as_of) return '';
    try {
      const d = new Date(data.as_of);
      return `Actualizado al ${d.toLocaleString('es-MX', {
        day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
      })}`;
    } catch {
      return data.as_of;
    }
  });

  readonly canSeeCost = this.productsAuth.canSeeCost;

  readonly report: HttpResourceRef<StockValueReportDto | undefined>;

  readonly rankedCategories = computed(() => {
    const cats = this.report.value()?.by_category ?? [];
    return [...cats].sort((a, b) => b.total_value - a.total_value);
  });

  readonly filteredItems = computed(() => {
    const data = this.report.value();
    if (!data) return [];
    const term = this.searchTerm().trim().toLowerCase();
    if (!term) return data.items;
    return data.items.filter((item) => {
      const haystack = `${item.name} ${item.category} ${item.product_id}`.toLowerCase();
      return haystack.includes(term);
    });
  });

  // ── Gráficos: líneas + dona ──
  readonly chartColors = ['#0f766e', '#6366f1', '#f59e0b', '#06b6d4', '#a78bfa', '#ef4444', '#22c55e', '#ec4899', '#84cc16', '#14b8a6'];

  readonly chartLabels = computed(() => this.rankedCategories().map((c) => c.category));

  readonly lineDatasets = computed(() => {
    const cats = this.rankedCategories();
    if (!cats.length) return [];
    return [{
      label: 'Valor por categoría',
      data: cats.map((c) => Math.round(c.total_value * 100) / 100),
      color: '#0f766e',
      type: 'line' as const,
      formatValue: 'currency' as const,
    }];
  });

  readonly donutData = computed<ChartData<'doughnut'>>(() => {
    const cats = this.rankedCategories();
    return {
      labels: cats.map((c) => c.category),
      datasets: [{
        data: cats.map((c) => Math.round(c.total_value * 100) / 100),
        backgroundColor: cats.map((_, i) => this.chartColors[i % this.chartColors.length]),
        borderColor: this.themeService.isDark() ? '#1e293b' : '#ffffff',
        borderWidth: 2,
        hoverOffset: 8,
        hoverBorderColor: this.themeService.isDark() ? '#1e293b' : '#ffffff',
      }],
    };
  });

  readonly donutOptions = computed<ChartConfiguration<'doughnut'>['options']>(() => {
    const isDark = this.themeService.isDark();
    const total = this.report.value()?.summary.total_stock_value || 1;
    return {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '62%',
      plugins: {
        legend: {
          position: 'bottom' as const,
          labels: {
            color: isDark ? '#8b949e' : '#5f6f87',
            font: { size: 11, family: 'Inter' },
            padding: 14,
            boxWidth: 10,
            usePointStyle: true,
            pointStyle: 'circle',
          },
        },
        tooltip: {
          backgroundColor: isDark ? '#161b22' : '#ffffff',
          titleColor: isDark ? '#e6edf3' : '#162033',
          bodyColor: isDark ? '#8b949e' : '#5f6f87',
          borderColor: isDark ? '#30363d' : '#d8e0eb',
          borderWidth: 1,
          padding: 10,
          callbacks: {
            label: (ctx) => {
              const val = (ctx.parsed as number) || 0;
              const pct = ((val / total) * 100).toFixed(1);
              return `${ctx.label}: $${val.toLocaleString('es-MX', { minimumFractionDigits: 2 })} (${pct}%)`;
            },
          },
        },
      },
    };
  });

  readonly isDonutEmpty = computed(() => this.rankedCategories().length === 0);

  constructor() {
    this.report = this.api.stockValueReport(this.propId);
  }

  onSearchInput(value: string): void {
    this.searchTerm.set(value);
  }

  categorySharePct(value: number, total: number): number {
    if (total === 0) return 0;
    return Math.round((value / total) * 100);
  }

  trackByProductId(_index: number, item: StockValueItemDto): string {
    return item.id;
  }
}
