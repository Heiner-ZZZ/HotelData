import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { SystemUserListItem, SystemUsersViewModel } from '../../models/system-users.model';
import { SystemUsersApiService } from '../../services/system-users-api.service';

type ColumnKey = 'username' | 'email' | 'primaryRole' | 'roles' | 'isActive' | 'createdAt';

interface ColumnFilter {
  column: ColumnKey;
  label: string;
  options: string[];
  selected: string;
  getValue: (item: SystemUserListItem) => string;
}

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
  readonly loadErrorMessage = signal('');
  readonly message = signal('');
  readonly errorMessage = signal('');
  readonly pendingUserId = signal<string | null>(null);
  readonly pendingDeleteId = signal<string | null>(null);
  readonly confirmDeleteId = signal<string | null>(null);
  readonly deletingId = signal<string | null>(null);
  readonly openSection = signal<string | null>(null);

  readonly openFilter = signal<ColumnKey | null>(null);
  readonly filters = signal<Record<ColumnKey, string>>({
    username: '',
    email: '',
    primaryRole: '',
    roles: '',
    isActive: '',
    createdAt: '',
  });

  readonly filterableItems = computed(() => {
    const vm = this.viewModel();
    if (!vm) return [];
    const f = this.filters();
    return vm.items.filter(item => {
      if (f.username && item.username !== f.username) return false;
      if (f.email && item.email !== f.email) return false;
      if (f.primaryRole && item.primaryRole !== f.primaryRole) return false;
      if (f.roles && item.roleNamesLabel !== f.roles) return false;
      if (f.isActive) {
        const activeLabel = item.isActive ? 'Activo' : 'Desactivado';
        if (activeLabel !== f.isActive) return false;
      }
      return true;
    });
  });

  readonly columnFilters = computed<ColumnFilter[]>(() => {
    const vm = this.viewModel();
    if (!vm) return [];
    const f = this.filters();
    return [
      {
        column: 'username',
        label: 'Usuario',
        options: this.uniqueValues(vm.items, i => i.username),
        selected: f.username,
        getValue: i => i.username,
      },
      {
        column: 'email',
        label: 'Email',
        options: this.uniqueValues(vm.items, i => i.email),
        selected: f.email,
        getValue: i => i.email,
      },
      {
        column: 'primaryRole',
        label: 'Rol principal',
        options: this.uniqueValues(vm.items, i => i.primaryRole),
        selected: f.primaryRole,
        getValue: i => i.primaryRole,
      },
      {
        column: 'roles',
        label: 'Roles',
        options: this.uniqueValues(vm.items, i => i.roleNamesLabel),
        selected: f.roles,
        getValue: i => i.roleNamesLabel,
      },
      {
        column: 'isActive',
        label: 'Activo',
        options: ['Activo', 'Desactivado'],
        selected: f.isActive,
        getValue: i => i.isActive ? 'Activo' : 'Desactivado',
      },
    ];
  });

  private uniqueValues(items: SystemUserListItem[], extract: (i: SystemUserListItem) => string): string[] {
    const seen = new Set<string>();
    return items.reduce<string[]>((acc, item) => {
      const val = extract(item);
      if (!seen.has(val)) {
        seen.add(val);
        acc.push(val);
      }
      return acc;
    }, []).sort((a, b) => a.localeCompare(b));
  }

  constructor() {
    this.loadUsers();
  }

  toggleSection(key: string) {
    this.openSection.update(v => v === key ? null : key);
  }

  toggleFilter(col: ColumnKey) {
    this.openFilter.update(v => v === col ? null : col);
  }

  setFilter(col: ColumnKey, value: string) {
    this.filters.update(f => ({ ...f, [col]: value }));
    this.openFilter.set(null);
  }

  clearFilters() {
    this.filters.set({
      username: '',
      email: '',
      primaryRole: '',
      roles: '',
      isActive: '',
      createdAt: '',
    });
  }

  get activeFilterCount(): number {
    const f = this.filters();
    return Object.values(f).filter(v => v !== '').length;
  }

  isFiltered(col: ColumnKey): boolean {
    return this.filters()[col] !== '';
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

  requestDelete(userId: string) {
    this.confirmDeleteId.set(userId);
    this.message.set('');
    this.errorMessage.set('');
  }

  cancelDelete() {
    this.confirmDeleteId.set(null);
  }

  confirmDelete(userId: string) {
    this.confirmDeleteId.set(null);
    this.deletingId.set(userId);
    this.message.set('');
    this.errorMessage.set('');

    this.api
      .deleteUser(userId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.message.set(result.message);
          this.deletingId.set(null);
          this.loadUsers();
        },
        error: (error) => {
          this.deletingId.set(null);
          this.errorMessage.set(error?.error?.message || 'No fue posible eliminar el usuario.');
        }
      });
  }

  onClickOutside(col: ColumnKey) {
    this.openFilter.update(v => v === col ? null : v);
  }

  private loadUsers() {
    this.viewState.set('loading');
    this.loadErrorMessage.set('');
    this.api
      .getUsers()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (vm) => {
          this.viewModel.set(vm);
          this.viewState.set(vm.items.length ? 'success' : 'empty');
        },
        error: (error: ApiError) => {
          this.loadErrorMessage.set(error.message || 'No fue posible cargar los usuarios.');
          this.viewState.set('error');
        }
      });
  }
}
