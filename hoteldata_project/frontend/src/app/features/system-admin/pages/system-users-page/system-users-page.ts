import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { SystemUsersViewModel } from '../../models/system-users.model';
import { SystemUsersApiService } from '../../services/system-users-api.service';

@Component({
  selector: 'app-system-users-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    StatusBadgeComponent
  ],
  templateUrl: './system-users-page.html',
  styleUrl: './system-users-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SystemUsersPageComponent {
  private readonly api = inject(SystemUsersApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<SystemUsersViewModel | null>(null);
  readonly message = signal('');
  readonly errorMessage = signal('');
  readonly pendingUserId = signal<string | null>(null);

  constructor() {
    this.loadUsers();
  }

  toggleUser(userId: string) {
    this.pendingUserId.set(userId);
    this.message.set('');
    this.errorMessage.set('');

    this.api
      .toggleUserActive(userId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.message.set(result.message);
          this.pendingUserId.set(null);
          this.loadUsers();
        },
        error: (error) => {
          this.pendingUserId.set(null);
          this.errorMessage.set(error?.error?.message || 'No fue posible actualizar el estado del usuario.');
        }
      });
  }

  private loadUsers() {
    this.viewState.set('loading');
    this.api
      .getUsers()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (vm) => {
          this.viewModel.set(vm);
          this.viewState.set(vm.items.length ? 'success' : 'empty');
        },
        error: () => {
          this.viewState.set('error');
        }
      });
  }
}
