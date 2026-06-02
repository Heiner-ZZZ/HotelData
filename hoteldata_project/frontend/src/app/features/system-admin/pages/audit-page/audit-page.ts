import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { AuditViewModel } from '../../models/audit.model';
import { AuditApiService } from '../../services/audit-api.service';

@Component({
  selector: 'app-audit-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    StatusBadgeComponent,
  ],
  templateUrl: './audit-page.html',
  styleUrl: './audit-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuditPageComponent {
  private readonly api = inject(AuditApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<AuditViewModel | null>(null);
  readonly loadErrorMessage = signal('');
  readonly openSection = signal<string | null>(null);

  constructor() {
    this.loadActivity();
  }

  toggleSection(key: string) {
    this.openSection.update(v => v === key ? null : key);
  }

  private loadActivity() {
    this.viewState.set('loading');
    this.loadErrorMessage.set('');
    this.api
      .getActivity()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (vm) => {
          this.viewModel.set(vm);
          this.viewState.set(vm.totalExecutions > 0 || vm.totalSearches > 0 ? 'success' : 'empty');
        },
        error: (error: ApiError) => {
          this.loadErrorMessage.set(error.message || 'No fue posible cargar la actividad.');
          this.viewState.set('error');
        },
      });
  }
}
