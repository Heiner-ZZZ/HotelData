import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { OwnershipApiService } from '../../services/ownership-api.service';
import type { OwnershipUserListItem, OwnershipRole } from '../../models/ownership.model';

@Component({
  selector: 'app-ownership-list-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    StatusBadgeComponent,
    RouterLink
  ],
  templateUrl: './ownership-list-page.html',
  styleUrl: './ownership-list-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class OwnershipListPageComponent {
  private readonly api = inject(OwnershipApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly viewState = signal<ViewState>('loading');
  readonly users = signal<OwnershipUserListItem[]>([]);
  readonly roles = signal<OwnershipRole[]>([]);
  readonly loadErrorMessage = signal('');
  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly roleMap = computed(() => {
    const map = new Map<string, string>();
    for (const r of this.roles()) {
      map.set(r.roleName, r.description);
    }
    return map;
  });

  constructor() {
    this.loadData();
  }

  private loadData() {
    this.viewState.set('loading');
    this.loadErrorMessage.set('');
    this.api.getUsers().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (vm) => {
        this.users.set(vm.users);
        this.roles.set(vm.roles);
        this.viewState.set(vm.users.length ? 'success' : 'empty');
      },
      error: (err: ApiError) => {
        this.loadErrorMessage.set(err.message || 'No fue posible cargar los usuarios.');
        this.viewState.set('error');
      }
    });
  }
}
