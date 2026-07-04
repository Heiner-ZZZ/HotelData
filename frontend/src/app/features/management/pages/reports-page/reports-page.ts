import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ManagementReportsViewModel } from '../../models/management-reports.model';
import { ManagementReportsApiService } from '../../services/management-reports-api.service';
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
  private readonly api = inject(ManagementReportsApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<ManagementReportsViewModel | null>(null);
  readonly errorMessage = signal('');

  constructor() {
    this.load();
  }

  retry() {
    this.load();
  }

  exportExcel() {
    const vm = this.viewModel();
    if (vm) {
      exportToExcel(vm).catch((err) => console.error('[Reports] Excel export failed', err));
    }
  }

  exportPdf() {
    const vm = this.viewModel();
    if (vm) {
      exportToPdf(vm).catch((err) => console.error('[Reports] PDF export failed', err));
    }
  }

  exportDocx() {
    const vm = this.viewModel();
    if (vm) {
      exportToDocx(vm).catch((err) => console.error('[Reports] DOCX export failed', err));
    }
  }

  private load() {
    this.viewState.set('loading');
    this.errorMessage.set('');
    this.api
      .getReports()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (vm) => {
          this.viewModel.set(vm);
          this.viewState.set(vm.topHotels.length || vm.operationalCounts.length ? 'success' : 'empty');
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible cargar los reportes operativos.');
          this.viewState.set('error');
        }
      });
  }
}
