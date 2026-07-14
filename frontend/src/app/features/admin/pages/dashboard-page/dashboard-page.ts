import { CurrencyPipe } from '@angular/common';
import { HttpClient, httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal, ViewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';

import { ToastService } from '../../../../shared/services/toast.service';
import { KpiChartComponent } from '../../../../shared/ui/kpi-chart/kpi-chart';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { MetricCardComponent } from '../../components/metric-card/metric-card';
import { OccupancySummaryComponent } from '../../components/occupancy-summary/occupancy-summary';
import { RecentReservationsComponent } from '../../components/recent-reservations/recent-reservations';
import { mapDashboardResponse } from '../../mappers/dashboard.mapper';
import type { DashboardApiResponseDto } from '../../models/dashboard.dto';
import type { DashboardViewModel } from '../../models/dashboard.model';
import type { WeeklyEarningPointDto } from '../../models/earnings.dto';
import type { WeeklyEarningPoint } from '../../models/earnings.model';

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

  private readonly http = inject(HttpClient);
  private readonly destroyRef = inject(DestroyRef);
  private readonly toast = inject(ToastService);

  // ─── Dashboard overview — httpResource nativo ────────
  readonly overview = httpResource<DashboardViewModel>(() => '/dashboard/overview', {
    parse: (dto) => mapDashboardResponse(dto as DashboardApiResponseDto),
  });

  // ─── Weekly earnings — httpResource nativo ───────────
  readonly weeklyEarnings = httpResource<WeeklyEarningPoint[]>(() => {
    if (this.isCustomRange()) {
      const sd = this.customStartDate();
      const ed = this.customEndDate();
      if (!sd || !ed) return undefined;
      return `/management/products/earnings/weekly?weeks=0&start_date=${sd}&end_date=${ed}`;
    }
    const weeksMap: Record<string, number> = { '3m': 13, '6m': 26, '12m': 52 };
    const weeks = weeksMap[this.activePreset()] ?? 52;
    return `/management/products/earnings/weekly?weeks=${weeks}`;
  }, {
    parse: (res) => (res as { items: WeeklyEarningPointDto[] }).items.map((dto) => ({
      label: dto.label,
      totalCommission: dto.total_commission,
      totalBookings: dto.total_bookings,
      paidCount: dto.paid_count,
      pendingCount: dto.pending_count,
    })),
  });

  // ─── Date range filter ───────────────────────────────
  readonly presets = [
    { id: '3m', label: '3 meses' },
    { id: '6m', label: '6 meses' },
    { id: '12m', label: '12 meses' },
  ] as const;

  readonly activePreset = signal<'3m' | '6m' | '12m'>('12m');
  readonly customStartDate = signal('');
  readonly customEndDate = signal('');
  readonly isCustomRange = signal(false);

  readonly chartLabels = computed(() => (this.weeklyEarnings.value() ?? []).map((w) => w.label));
  readonly chartDatasets = computed(() => {
    const data = this.weeklyEarnings.value() ?? [];
    return [
      {
        label: 'Comisiones',
        data: data.map((w) => w.totalCommission),
        color: '#22c55e',
      },
      {
        label: 'Reservas',
        data: data.map((w) => w.totalBookings),
        color: '#1463ff',
      },
    ];
  });

  readonly totalCommission = computed(() =>
    (this.weeklyEarnings.value() ?? []).reduce((sum, w) => sum + w.totalCommission, 0),
  );
  readonly totalBookings = computed(() =>
    (this.weeklyEarnings.value() ?? []).reduce((sum, w) => sum + w.totalBookings, 0),
  );

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

  onRetry() {
    this.overview.reload();
  }

  setPreset(preset: '3m' | '6m' | '12m') {
    this.activePreset.set(preset);
    this.isCustomRange.set(false);
  }

  applyCustomRange() {
    if (!this.customStartDate() || !this.customEndDate()) return;
    this.isCustomRange.set(true);
  }

  clearCustomRange() {
    this.customStartDate.set('');
    this.customEndDate.set('');
    this.isCustomRange.set(false);
    this.activePreset.set('12m');
    this.overview.reload();
  }

  refreshKpis(): void {
    this.http
      .post<{ ok: boolean; display_message: string }>('/dashboard/kpis/refresh', {})
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          if (result.ok) {
            this.toast.show(result.display_message, 'info', 5000);
            this.overview.reload();
          } else {
            this.toast.show('No se pudieron actualizar los indicadores.', 'error', 5000);
          }
        },
        error: (err: unknown) => {
          const apiErr = err as { message?: string };
          this.toast.show(apiErr.message || 'Error al refrescar los indicadores del panel.', 'error', 5000);
        },
      });
  }
}
