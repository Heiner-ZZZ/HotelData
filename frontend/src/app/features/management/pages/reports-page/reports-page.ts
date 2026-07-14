import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { RouterLink } from '@angular/router';

import { ReportsExportService } from '../../../../shared/services/reports-export.service';
import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ManagementReportsViewModel } from '../../models/management-reports.model';
import type { ManagementReportsDto } from '../../models/management-reports.dto';
import { ManagementReportsApiService } from '../../services/management-reports-api.service';
import { mapManagementReports } from '../../mappers/management-reports.mapper';
import { exportToExcel, exportToPdf, exportToDocx } from '../../utils/export-reports.utils';

@Component({
  selector: 'app-management-reports-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    RouterLink
  ],
  templateUrl: './reports-page.html',
  styleUrl: './reports-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ManagementReportsPageComponent {
  private readonly reports = inject(ReportsExportService);

  readonly reportsResource = httpResource<ManagementReportsViewModel>(() => '/api/management/reports', {
    parse: (dto) => mapManagementReports(dto as ManagementReportsDto),
  });

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
