import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import { ToastService } from '../../../../shared/services/toast.service';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { SystemUserListItem, SystemUsersViewModel } from '../../models/system-users.model';
import { SystemUsersApiService } from '../../services/system-users-api.service';

type ColumnKey = 'username' | 'email' | 'primaryRole' | 'roles' | 'isActive';

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
    FormsModule,
    LoadingStateComponent,
    PageHeaderComponent,
    StatusBadgeComponent,
  ],
  templateUrl: './system-users-page.html',
  styleUrl: './system-users-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SystemUsersPageComponent {
  private readonly api = inject(SystemUsersApiService);
  private readonly toast = inject(ToastService);
  private readonly destroyRef = inject(DestroyRef);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<SystemUsersViewModel | null>(null);
  readonly loadErrorMessage = signal('');

  readonly searchQuery = signal('');
  readonly pendingUserId = signal<string | null>(null);
  readonly confirmDeleteId = signal<string | null>(null);
  readonly deletingId = signal<string | null>(null);

  readonly openFilter = signal<ColumnKey | null>(null);
  readonly filters = signal<Record<ColumnKey, string>>({
    username: '',
    email: '',
    primaryRole: '',
    roles: '',
    isActive: '',
  });

  readonly filteredItems = computed(() => {
    const vm = this.viewModel();
    if (!vm) return [];
    const f = this.filters();
    const q = this.searchQuery().toLowerCase().trim();
    return vm.items.filter((item) => {
      if (f.username && item.username !== f.username) return false;
      if (f.email && item.email !== f.email) return false;
      if (f.primaryRole && item.primaryRole !== f.primaryRole) return false;
      if (f.roles && item.roleNamesLabel !== f.roles) return false;
      if (f.isActive) {
        const activeLabel = item.isActive ? 'Activo' : 'Inactivo';
        if (activeLabel !== f.isActive) return false;
      }
      if (q && !item.username.toLowerCase().includes(q) && !item.email.toLowerCase().includes(q)) {
        return false;
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
        options: this.uniqueValues(vm.items, (i) => i.username),
        selected: f.username,
        getValue: (i) => i.username,
      },
      {
        column: 'email',
        label: 'Email',
        options: this.uniqueValues(vm.items, (i) => i.email),
        selected: f.email,
        getValue: (i) => i.email,
      },
      {
        column: 'primaryRole',
        label: 'Rol principal',
        options: this.uniqueValues(vm.items, (i) => i.primaryRole),
        selected: f.primaryRole,
        getValue: (i) => i.primaryRole,
      },
      {
        column: 'roles',
        label: 'Roles',
        options: this.uniqueValues(vm.items, (i) => i.roleNamesLabel),
        selected: f.roles,
        getValue: (i) => i.roleNamesLabel,
      },
      {
        column: 'isActive',
        label: 'Estado',
        options: ['Activo', 'Inactivo'],
        selected: f.isActive,
        getValue: (i) => (i.isActive ? 'Activo' : 'Inactivo'),
      },
    ];
  });

  private uniqueValues(items: SystemUserListItem[], extract: (i: SystemUserListItem) => string): string[] {
    const seen = new Set<string>();
    return items
      .reduce<string[]>((acc, item) => {
        const val = extract(item);
        if (!seen.has(val)) {
          seen.add(val);
          acc.push(val);
        }
        return acc;
      }, [])
      .sort((a, b) => a.localeCompare(b));
  }

  constructor() {
    this.loadUsers();
  }

  toggleFilter(col: ColumnKey) {
    this.openFilter.update((v) => (v === col ? null : col));
  }

  setFilter(col: ColumnKey, value: string) {
    this.filters.update((f) => ({ ...f, [col]: value }));
    this.openFilter.set(null);
  }

  clearFilters() {
    this.filters.set({
      username: '',
      email: '',
      primaryRole: '',
      roles: '',
      isActive: '',
    });
    this.searchQuery.set('');
  }

  get activeFilterCount(): number {
    const f = this.filters();
    return Object.values(f).filter((v) => v !== '').length;
  }

  isFiltered(col: ColumnKey): boolean {
    return this.filters()[col] !== '';
  }

  hasActiveFilters(): boolean {
    return this.activeFilterCount > 0 || this.searchQuery().trim().length > 0;
  }

  toggleUser(userId: string) {
    this.pendingUserId.set(userId);
    this.api
      .toggleUserActive(userId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.toast.success(result.message);
          this.pendingUserId.set(null);
          this.loadUsers();
        },
        error: (err) => {
          this.pendingUserId.set(null);
          this.toast.error(err?.error?.message || 'No fue posible actualizar el estado del usuario.');
        },
      });
  }

  requestDelete(userId: string) {
    this.confirmDeleteId.set(userId);
  }

  cancelDelete() {
    this.confirmDeleteId.set(null);
  }

  confirmDelete(userId: string) {
    this.confirmDeleteId.set(null);
    this.deletingId.set(userId);
    this.api
      .deleteUser(userId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.toast.success(result.message);
          this.deletingId.set(null);
          this.loadUsers();
        },
        error: (err) => {
          this.deletingId.set(null);
          this.toast.error(err?.error?.message || 'No fue posible eliminar el usuario.');
        },
      });
  }

  onClickOutside(col: ColumnKey) {
    this.openFilter.update((v) => (v === col ? null : v));
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
        },
      });
  }
}
