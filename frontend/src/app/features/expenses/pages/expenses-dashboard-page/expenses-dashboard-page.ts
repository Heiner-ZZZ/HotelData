import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import { BaseChartDirective } from 'ng2-charts';

import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { ThemeService } from '../../../../core/theme/theme.service';
import { ExpensesApiService } from '../../services/expenses-api.service';
import { mapExpenseDashboard } from '../../mappers/expenses.mapper';
import type { ExpenseDashboard } from '../../models/expenses.model';
import type { ExpenseDashboardDto } from '../../models/expenses.dto';

Chart.register(...registerables);

@Component({
  selector: 'app-expenses-dashboard-page',
  standalone: true,
  imports: [CurrencyPipe, RouterLink, PageHeaderComponent, LoadingStateComponent, BaseChartDirective],
  styleUrl: '../../expenses.shared.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page-wrap">
      <app-page-header
        eyebrow="Financeiro"
        title="Control de Gastos y Compras"
        description="Visión general del estado financiero operativo."
      />

      <div class="actions-row">
        <a class="btn" [routerLink]="['/management/expenses/invoices']">
          Ver Facturas
        </a>
        <a class="btn btn--primary" [routerLink]="['/management/expenses/invoices/new']">
          <span class="material-symbols-outlined icon">add</span> Nueva Factura
        </a>
        <a class="btn btn--secondary" [routerLink]="['/management/expenses/ledger']">
          <span class="material-symbols-outlined icon">account_balance</span> Libro Mayor
        </a>
      </div>

      @switch (viewState()) {
        @case ('loading') { <app-loading-state label="Cargando dashboard..." /> }
        @case ('error') { <div class="error-line" style="padding: 40px;">Error al cargar el dashboard.</div> }
        @default {
          @if (data(); as d) {
            <!-- KPI Cards -->
            <div class="kpi-grid">
              <!-- KPI 1: Total expenses -->
              <div class="card">
                <div class="kpi-decor kpi-decor--red"></div>
                <div class="kpi-row-head">
                  <span class="kpi-label">Gastos Totales (Mes)</span>
                  <span class="material-symbols-outlined" style="color: var(--danger); font-size: 20px;">trending_up</span>
                </div>
                <div class="kpi-value">{{ d.monthTotal | currency:'MXN':'symbol-narrow':'1.0-0' }}</div>
              </div>

              <!-- KPI 2: Budget execution -->
              <div class="card">
                <div class="kpi-decor kpi-decor--blue"></div>
                <div class="kpi-row-head">
                  <span class="kpi-label">Presupuesto Ejecutado</span>
                  <span class="material-symbols-outlined" style="color: var(--accent); font-size: 20px;">account_balance_wallet</span>
                </div>
                <div class="kpi-value">{{ d.budgetExecutionPct }}%</div>
                <div class="progress">
                  <div class="progress__fill" [style.width.%]="d.budgetExecutionPct"></div>
                </div>
                <div class="foot-note">Quedan {{ d.budgetRemaining | currency:'MXN':'symbol-narrow':'1.0-0' }}</div>
              </div>

              <!-- KPI 3: Pending approval -->
              <div class="card">
                <div class="kpi-decor kpi-decor--amber"></div>
                <div class="kpi-row-head">
                  <span class="kpi-label">Pendiente de Aprobación</span>
                  <span class="material-symbols-outlined" style="color: var(--warning); font-size: 20px;">pending_actions</span>
                </div>
                <div class="kpi-value">{{ d.pendingCount }}</div>
                <div class="kpi-value--warning">Valor: {{ d.pendingValue | currency:'MXN':'symbol-narrow':'1.0-0' }}</div>
              </div>
            </div>

            <!-- Bar Chart: Monthly Evolution -->
            @if (d.monthlyBreakdown.length > 1) {
              <div class="card card--mb-24">
                <div class="section-heading-row">
                  <h3 class="section-heading">Evolución de Gastos Mensuales</h3>
                  <span class="section-eyebrow">Últimos {{ d.monthlyBreakdown.length }} meses</span>
                </div>
                <div style="height: 260px; position: relative;">
                  <canvas
                    baseChart
                    [data]="barChartData()"
                    [options]="barChartOptions()"
                    [type]="'bar'"
                    style="width: 100%; height: 100%;"
                  ></canvas>
                </div>
              </div>
            }

            <!-- Bottom: Categories breakdown -->
            <div class="card">
              <h3 class="section-heading" style="margin: 0 0 16px;">Gastos por Categoría</h3>
              @if (d.byCategory.length > 0) {
                <div class="cat-row--vertical">
                  @for (cat of d.byCategory; track cat.category) {
                    <div class="cat-row">
                      <span class="cat-row__name">{{ cat.category }}</span>
                      <div class="cat-row__progress">
                        <div class="cat-row__progress-fill"
                          [style.width.%]="d.totalBudget > 0 ? (cat.total / d.totalBudget * 100) : 0"></div>
                      </div>
                      <span class="cat-row__amount">{{ cat.total | currency:'MXN':'symbol-narrow':'1.0-0' }}</span>
                      <span class="cat-row__count">{{ cat.count }} fact.</span>
                    </div>
                  }
                </div>
              } @else {
                <p class="empty-line">No hay datos de gastos por categoría.</p>
              }
            </div>
          }
        }
      }
    </div>
  `,
})
export class ExpensesDashboardPageComponent {
  private readonly expensesApi = inject(ExpensesApiService);
  private readonly themeService = inject(ThemeService);

  readonly dashboardResource = httpResource<ExpenseDashboard>(
    () => `/api/expenses/dashboard`,
    { parse: (dto) => mapExpenseDashboard(dto as ExpenseDashboardDto) },
  );

  readonly data = computed(() => this.dashboardResource.value());

  readonly viewState = computed(() => {
    if (this.dashboardResource.error()) return 'error' as const;
    if (this.dashboardResource.isLoading()) return 'loading' as const;
    return 'success' as const;
  });

  readonly barChartData = signal<{ labels: string[]; datasets: { label: string; data: number[]; backgroundColor: string | string[]; borderColor: string; borderWidth: number; borderRadius: number; }[] }>({ labels: [], datasets: [] });

  /**
   * Read design tokens for chart axis colors. Subscribes to
   * `ThemeService.isDark()` so the resolved colors update reactively
   * when the user toggles dark mode — ng2-charts picks up the new
   * options signal and calls `chart.update()` automatically.
   *
   * Tokens consumed:
   *  - `--muted-text`  → axis tick labels (light `#5f6f87` / dark `#8b949e`)
   *  - `--gray-100`    → y-axis grid line (light `#f3f4f6` / dark `#1c2333`)
   *
   * Out of scope: `tooltip.backgroundColor` in the parent barChartOptions
   * remains hardcoded (`#1e293b`) — the chart's axes are theme-aware but
   * the tooltip still renders dark in both themes. Don't be misled into
   * thinking the chart is fully theme-aware when reading this file.
   *
   * SSR-safe guard: `typeof document === 'undefined'` returns the
   * LIGHT theme's token literals so non-browser contexts (jest,
   * server prerender) keep a hue-correct, if stale, color.
   */
  private readonly chartTheme = computed(() => {
    // Reading `isDark()` registers the reactive subscription — only the
    // subscription matters; the value itself is unused.
    this.themeService.isDark();
    if (typeof document === 'undefined') {
      // SSR / jest fallback. Use the LIGHT theme's TOKEN LITERAL values
      // (not the prior hardcoded slate-400 / slate-100) so the hue
      // matches the resolved token bit-for-bit when the page hydrates.
      return { ticks: '#5f6f87', grid: '#f3f4f6' };
    }
    const root = document.documentElement;
    const muted = getComputedStyle(root).getPropertyValue('--muted-text').trim() || '#5f6f87';
    const gray100 = getComputedStyle(root).getPropertyValue('--gray-100').trim() || '#f3f4f6';
    return { ticks: muted, grid: gray100 };
  });

  readonly barChartOptions = computed<any>(() => {
    const c = this.chartTheme();
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          // Unchanged intentionally — out of scope per user request.
          backgroundColor: '#1e293b',
          titleFont: { family: 'Inter', size: 12 },
          bodyFont: { family: 'Inter', size: 13 },
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            label: (ctx: any) => `MXN ${ctx.parsed.y.toLocaleString('es-MX')}`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: {
            font: { family: 'Inter', size: 11 },
            color: c.ticks,
            maxRotation: 0,
          },
        },
        y: {
          grid: { color: c.grid, drawBorder: false },
          ticks: {
            font: { family: 'Inter', size: 11 },
            color: c.ticks,
            callback: (val: any) => `${(val / 1000).toFixed(0)}k`,
          },
          beginAtZero: true,
        },
      },
    };
  });

  constructor() {
    effect(() => {
      const d = this.data();
      if (d) {
        this.buildChartData(d);
      }
    });
  }

  private buildChartData(d: ExpenseDashboard): void {
    if (!d.monthlyBreakdown || d.monthlyBreakdown.length === 0) return;

    const months: Record<string, string> = {
      '01': 'Ene', '02': 'Feb', '03': 'Mar', '04': 'Abr',
      '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Ago',
      '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dic',
    };
    const labels = d.monthlyBreakdown.map((m) => {
      const parts = m.month.split('-');
      const monthLabel = months[parts[1]] || parts[1];
      return `${monthLabel} ${parts[0]}`;
    });
    const values = d.monthlyBreakdown.map((m) => m.total);

    const maxVal = Math.max(...values);
    const gradientColors = values.map((v) => {
      const ratio = maxVal > 0 ? v / maxVal : 0.3;
      const opacity = 0.4 + ratio * 0.6;
      return `rgba(37, 99, 235, ${opacity})`;
    });

    this.barChartData.set({
      labels,
      datasets: [
        {
          label: 'Gastos',
          data: values,
          backgroundColor: gradientColors,
          borderColor: '#2563eb',
          borderWidth: 1,
          borderRadius: 4,
        },
      ],
    });
  }
}
