import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal, ViewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';

import type { ApiError } from '../../../../core/api/api-error.model';
import { toast } from '../../../../core/toast/toast.service';
import { KpiChartComponent } from '../../../../shared/ui/kpi-chart/kpi-chart';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { MetricCardComponent } from '../../components/metric-card/metric-card';
import { OccupancySummaryComponent } from '../../components/occupancy-summary/occupancy-summary';
import { RecentReservationsComponent } from '../../components/recent-reservations/recent-reservations';
import type { DashboardViewModel } from '../../models/dashboard.model';
import type { WeeklyEarningPoint } from '../../models/earnings.model';
import { DashboardApiService } from '../../services/dashboard-api.service';
import { EarningsApiService } from '../../services/earnings-api.service';

@Component({
  selector: 'app-dashboard-page',
  imports: [
    CurrencyPipe,
    EmptyStateComponent,
    ErrorStateComponent,
    FormsModule,
    KpiChartComponent,
    LoadingStateComponent,
    MetricCardComponent,
    OccupancySummaryComponent,
    PageHeaderComponent,
    RecentReservationsComponent
  ],
  templateUrl: './dashboard-page.html',
  styleUrl: './dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class DashboardPageComponent {
  @ViewChild('earningsChart') private readonly earningsChartComponent?: KpiChartComponent;

  private readonly dashboardApi = inject(DashboardApiService);
  private readonly earningsApi = inject(EarningsApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<DashboardViewModel | null>(null);
  readonly errorMessage = signal('');

  readonly weeklyEarnings = signal<WeeklyEarningPoint[]>([]);
  readonly chartLabels = computed(() => this.weeklyEarnings().map((w) => w.label));
  readonly chartDatasets = computed(() => [
    {
      label: 'Comisiones',
      data: this.weeklyEarnings().map((w) => w.totalCommission),
      color: '#22c55e',
    },
    {
      label: 'Reservas',
      data: this.weeklyEarnings().map((w) => w.totalBookings),
      color: '#1463ff',
    },
  ]);

  readonly totalCommission = computed(() =>
    this.weeklyEarnings().reduce((sum, w) => sum + w.totalCommission, 0),
  );
  readonly totalBookings = computed(() =>
    this.weeklyEarnings().reduce((sum, w) => sum + w.totalBookings, 0),
  );

  // ─── Date range filter ───────────────────────────────────
  readonly presets = [
    { id: '3m', label: '3 meses' },
    { id: '6m', label: '6 meses' },
    { id: '12m', label: '12 meses' },
  ] as const;

  readonly activePreset = signal<'3m' | '6m' | '12m'>('12m');
  readonly customStartDate = signal('');
  readonly customEndDate = signal('');
  readonly isCustomRange = signal(false);

  readonly rangeLabel = computed(() => {
    if (this.isCustomRange()) {
      const s = this.customStartDate();
      const e = this.customEndDate();
      return s || e ? `${s || '…'} → ${e || '…'}` : 'Personalizado';
    }
    const preset = this.presets.find((p) => p.id === this.activePreset());
    return `Últimos ${preset?.label ?? '12 meses'}`;
  });

  readonly chartTitle = computed(() => `Ganancias semanales — ${this.rangeLabel()}`);

  exportChart() {
    const today = new Date().toISOString().slice(0, 10);
    this.earningsChartComponent?.exportImage(`ganancias-semanales-${today}`);
  }

  constructor() {
    this.loadDashboard();
    this.loadWeeklyEarnings();
  }

  onRetry() {
    this.loadDashboard();
  }

  setPreset(preset: '3m' | '6m' | '12m') {
    this.activePreset.set(preset);
    this.isCustomRange.set(false);
    this.loadWeeklyEarnings();
  }

  applyCustomRange() {
    if (!this.customStartDate() || !this.customEndDate()) return;
    this.isCustomRange.set(true);
    this.loadWeeklyEarnings();
  }

  clearCustomRange() {
    this.customStartDate.set('');
    this.customEndDate.set('');
    this.isCustomRange.set(false);
    this.activePreset.set('12m');
    this.loadWeeklyEarnings();
  }
    this.loadDashboard();
  }

  refreshKpis(): void {
    this.dashboardApi
      .refreshKpis()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          if (result.ok) {
            toast(result.display_message, 'dark', 5000);
            this.loadDashboard();
          } else {
            toast('No se pudieron actualizar los indicadores.', 'error', 5000);
          }
        },
        error: (err: ApiError) => {
          toast(err.message || 'Error al refrescar los indicadores del panel.', 'error', 5000);
        },
      });
  }

  private loadDashboard() {
    this.viewState.set('loading');
    this.errorMessage.set('');

    this.dashboardApi
      .getOverview()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (viewModel) => {
          this.viewModel.set(viewModel);
          this.viewState.set(viewModel.kpis.length ? 'success' : 'empty');
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible cargar los indicadores del panel.');
          this.viewState.set('error');
        }
      });
  }

  private loadWeeklyEarnings() {
    if (this.isCustomRange()) {
      const sd = this.customStartDate();
      const ed = this.customEndDate();
      if (!sd || !ed) return;

      this.earningsApi
        .getWeeklyEarnings(0, sd, ed)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (data) => this.weeklyEarnings.set(data),
          error: () => {
            // Silently fail
          },
        });
      return;
    }

    // Preset-based: compute weeks
    const weeksMap: Record<string, number> = { '3m': 13, '6m': 26, '12m': 52 };
    const weeks = weeksMap[this.activePreset()] ?? 52;

    this.earningsApi
      .getWeeklyEarnings(weeks)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => this.weeklyEarnings.set(data),
        error: () => {
          // Silently fail
        },
      });
  }
}
