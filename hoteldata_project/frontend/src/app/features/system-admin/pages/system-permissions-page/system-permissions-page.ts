import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { SystemPermissionsViewModel } from '../../models/system-permissions.model';
import { SystemPermissionsApiService } from '../../services/system-permissions-api.service';

@Component({
  selector: 'app-system-permissions-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent
  ],
  templateUrl: './system-permissions-page.html',
  styleUrl: './system-permissions-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SystemPermissionsPageComponent {
  private readonly api = inject(SystemPermissionsApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<SystemPermissionsViewModel | null>(null);

  constructor() {
    this.api
      .getPermissionsOverview()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (vm) => {
          this.viewModel.set(vm);
          this.viewState.set(vm.permissions.length ? 'success' : 'empty');
        },
        error: () => {
          this.viewState.set('error');
        }
      });
  }
}
