import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { DecimalPipe } from '@angular/common';

import { ReportsExportService } from '../../../../shared/services/reports-export.service';
import { AuthService } from '../../../../core/auth/auth.service';
import { REPORTS_DOWNLOAD } from '../../../../core/auth/permission.constants';
import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { HorizontalSubNavComponent } from '../../../../shared/ui/horizontal-sub-nav/horizontal-sub-nav';
import { KpiChartComponent } from '../../../../shared/ui/kpi-chart/kpi-chart';
import type { KpiChartDataset } from '../../../../shared/ui/kpi-chart/kpi-chart';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ManagementReportsViewModel } from '../../models/management-reports.model';
import type { ManagementReportsDto } from '../../models/management-reports.dto';
import { mapManagementReports } from '../../mappers/management-reports.mapper';
import { exportToExcel, exportToPdf, exportToDocx } from '../../utils/export-reports.utils';

@Component({
  selector: 'app-management-reports-page',
  imports: [
    DecimalPipe,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    RouterLink,
    HorizontalSubNavComponent,
    KpiChartComponent
  ],
  templateUrl: './reports-page.html',
  styleUrl: './reports-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ManagementReportsPageComponent {
  private readonly reports = inject(ReportsExportService);
  private readonly auth = inject(AuthService);

  /** Descarga de reportes gateada por ``reports.download``. */
  readonly canExport = computed(() => this.auth.hasPermission(REPORTS_DOWNLOAD));

  /** Página de la tabla de registros (patrón compuesto táctico). */
  readonly page = signal(1);
  readonly pageSize = 10;

  private buildUrl(): string {
    const params = new URLSearchParams();
    params.set('page', String(this.page()));
    params.set('page_size', String(this.pageSize));
    return `/api/management/reports?${params.toString()}`;
  }

  readonly reportsResource = httpResource<ManagementReportsViewModel>(() => this.buildUrl(), {
    parse: (dto) => mapManagementReports(dto as ManagementReportsDto),
  });

  /** Datasets del gráfico compuesto (KPIs → gráfico → tabla de registros). */
  readonly chartDatasets = computed<KpiChartDataset[]>(() => {
    const series = this.reportsResource.value()?.series;
    if (!series) return [];
    return series.datasets.map((d) => ({
      label: d.label,
      data: d.data,
      formatValue: (d.label.includes('Revenue') ? 'currency' : 'number') as 'currency' | 'number',
    }));
  });

  readonly chartLabels = computed(() => this.reportsResource.value()?.series.labels ?? []);

  goToPage(page: number): void {
    const vm = this.reportsResource.value();
    if (!vm) return;
    const next = Math.min(Math.max(1, page), vm.totalPages);
    if (next !== vm.page) {
      this.page.set(next);
    }
  }

  formatMonth(val: string): string {
    if (!val) return '—';
    const d = new Date(`${val}-01T00:00:00`);
    if (isNaN(d.getTime())) return val;
    return d.toLocaleDateString('es-MX', { month: 'short', year: 'numeric' });
  }

  readonly viewState = computed<ViewState>(() => {
    if (this.reportsResource.isLoading()) return 'loading';
    if (this.reportsResource.error()) return 'error';
    const vm = this.reportsResource.value();
    if (!vm) return 'loading';
    return vm.topHotels.length || vm.operationalCounts.length ? 'success' : 'empty';
  });

  readonly errorMessage = computed(() => {
    const err = this.reportsResource.error();
    return (err as unknown as ApiError)?.message || '';
  });

  retry() {
    this.reportsResource.reload();
  }

  exportExcel() {
    const vm = this.reportsResource.value();
    if (vm) {
      exportToExcel(vm, this.reports).catch((err) => console.error('[Reports] Excel export failed', err));
    }
  }

  exportPdf() {
    const vm = this.reportsResource.value();
    if (vm) {
      exportToPdf(vm, this.reports).catch((err) => console.error('[Reports] PDF export failed', err));
    }
  }

  exportDocx() {
    const vm = this.reportsResource.value();
    if (vm) {
      exportToDocx(vm).catch((err) => console.error('[Reports] DOCX export failed', err));
    }
  }
}
