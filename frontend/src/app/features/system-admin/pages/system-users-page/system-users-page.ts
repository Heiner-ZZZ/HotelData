import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { FormsModule } from '@angular/forms';

import { ConfirmDialogComponent } from '../../../../shared/ui/confirm-dialog/confirm-dialog.component';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import { ToastService } from '../../../../shared/services/toast.service';
import { OperationModeService } from '../../../../core/services/operation-mode.service';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { AssignedHotel, SystemUserListItem, SystemUsersViewModel } from '../../models/system-users.model';
import type { SystemUsersResponseDto } from '../../models/system-users.dto';
import { SystemUsersApiService } from '../../services/system-users-api.service';
import { mapSystemUsersResponse } from '../../mappers/system-users.mapper';
import { roleLabel } from '../../../../core/auth/role-labels';

type ColumnKey = 'username' | 'email' | 'primaryRole' | 'roles' | 'isActive';

/** Roles que operan sobre hoteles concretos y requieren hoteles asignados.
 *  Espejo de ``HOTEL_ROLES`` en server/src/app/modules/admin/service/ownership.py. */
const HOTEL_ROLES = new Set(['hotel_partner', 'gerente_hotel', 'revenue_manager', 'marketing_hotelero', 'maintenance']);

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
    ConfirmDialogComponent,
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
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly opMode = inject(OperationModeService);
  private readonly destroyRef = inject(DestroyRef);

  constructor() {
    // Si la página se destruye con el modal abierto, no dejar el chip del nav
    // pegado en modo de escritura (misma guarda que currencies/amenities).
    this.destroyRef.onDestroy(() => this.opMode.reset());

    // Debounce de 350ms para la búsqueda de hoteles dentro del modal.
    effect((onCleanup) => {
      const q = this.hotelQuery();
      const timer = setTimeout(() => {
        if (!q.trim()) {
          this.hotelResults.set([]);
          this.hotelSearching.set(false);
          return;
        }
        this.hotelSearching.set(true);
        this.api.searchHotels(q.trim()).subscribe({
          next: (results) => {
            this.hotelResults.set(results);
            this.hotelSearching.set(false);
          },
          error: () => {
            this.hotelResults.set([]);
            this.hotelSearching.set(false);
          },
        });
      }, 350);
      onCleanup(() => clearTimeout(timer));
    });
  }

  readonly usersResource = httpResource<SystemUsersViewModel>(() => '/api/admin/users', {
    parse: (dto) => mapSystemUsersResponse(dto as SystemUsersResponseDto),
  });

  readonly viewState = computed<ViewState>(() => {
    if (this.usersResource.isLoading()) return 'loading';
    if (this.usersResource.error()) return 'error';
    const vm = this.usersResource.value();
    if (!vm) return 'loading';
    return vm.items.length ? 'success' : 'empty';
  });

  readonly roleLabel = roleLabel;

  readonly loadErrorMessage = computed(() => {
    const err = this.usersResource.error();
    return (err as unknown as ApiError)?.message || '';
  });

  readonly searchQuery = signal('');
  readonly pendingUserId = signal<string | null>(null);
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
    const vm = this.usersResource.value();
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
    const vm = this.usersResource.value();
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

  async toggleUser(userId: string, username: string, currentLabel: string) {
    const action = currentLabel === 'Activar' ? 'activar' : 'desactivar';
    const confirmed = await this.confirmDialog.open({
      title: `${currentLabel} usuario`,
      message: `¿Estás seguro de que deseas ${action} al usuario «${username}»?`,
      variant: currentLabel === 'Desactivar' ? 'warning' : 'default',
      confirmLabel: currentLabel,
      cancelLabel: 'Cancelar',
    });
    if (!confirmed) return;

    this.pendingUserId.set(userId);
    this.api
      .toggleUserActive(userId)
      .subscribe({
        next: (result) => {
          this.toast.success(result.message);
          this.pendingUserId.set(null);
          this.usersResource.reload();
        },
        error: (err) => {
          this.pendingUserId.set(null);
          this.toast.error(err?.error?.message || 'No fue posible actualizar el estado del usuario.');
        },
      });
  }

  // ── Edit modal ────────────────────────────────────────────────────────

  readonly editingUser = signal<SystemUserListItem | null>(null);
  readonly editForm = signal({
    username: '',
    displayName: '',
    email: '',
    primaryRole: '',
    password: '',
    assignedHotels: [] as AssignedHotel[],
  });
  readonly savingEdit = signal(false);

  readonly roleOptions = computed(() => this.usersResource.value()?.roles ?? []);

  readonly selectedRoleDescription = computed(() => {
    const role = this.roleOptions().find((r) => r.roleName === this.editForm().primaryRole);
    return role?.description ?? '';
  });

  openEdit(user: SystemUserListItem) {
    this.editingUser.set(user);
    this.editForm.set({
      username: user.username,
      displayName: user.displayName,
      email: user.email,
      primaryRole: user.primaryRole,
      password: '',
      assignedHotels: user.assignedHotels.map((h) => ({ ...h })),
    });
    this.hotelQuery.set('');
    this.hotelResults.set([]);
    this.opMode.setMode('update', user.username);
  }

  closeEdit() {
    this.editingUser.set(null);
    this.savingEdit.set(false);
    this.opMode.reset();
  }

  saveEdit() {
    const user = this.editingUser();
    if (!user) return;

    const f = this.editForm();
    const username = f.username.trim();
    const displayName = f.displayName.trim();
    const email = f.email.trim().toLowerCase();
    if (!username) {
      this.toast.error('El nombre de usuario no puede quedar vacío.');
      return;
    }
    if (/\s/.test(username)) {
      this.toast.error('El nombre de usuario no puede contener espacios.');
      return;
    }
    if (!displayName) {
      this.toast.error('El nombre mostrado no puede quedar vacío.');
      return;
    }
    if (!email.includes('@')) {
      this.toast.error('Formato de email inválido.');
      return;
    }
    if (this.isHotelRole(f.primaryRole) && f.assignedHotels.length === 0) {
      this.toast.error('Un usuario con rol de hotel debe tener al menos un hotel asignado.');
      return;
    }

    const payload: Record<string, string | number[]> = {
      username,
      display_name: displayName,
      email,
      primary_role: f.primaryRole,
    };
    if (this.isHotelRole(f.primaryRole)) {
      payload['assigned_hotels'] = f.assignedHotels.map((h) => h.propId);
    }
    if (f.password.trim()) {
      if (f.password.trim().length < 6) {
        this.toast.error('La contraseña debe tener al menos 6 caracteres.');
        return;
      }
      payload['password'] = f.password.trim();
    }

    this.savingEdit.set(true);
    this.api.updateUser(user.userId, payload).subscribe({
      next: (result) => {
        this.savingEdit.set(false);
        this.closeEdit();
        this.usersResource.reload();
        this.toast.success(result.message || 'Usuario actualizado correctamente.');
      },
      error: (err) => {
        this.savingEdit.set(false);
        this.toast.error(err?.error?.message || 'No fue posible actualizar el usuario.');
      },
    });
  }

  // ── Hotel selector (solo roles de hotel) ─────────────────────────────

  readonly hotelQuery = signal('');
  readonly hotelResults = signal<AssignedHotel[]>([]);
  readonly hotelSearching = signal(false);

  isHotelRole(role: string): boolean {
    return HOTEL_ROLES.has(role);
  }

  isHotelSelected(propId: number): boolean {
    return this.editForm().assignedHotels.some((h) => h.propId === propId);
  }

  toggleHotel(hotel: AssignedHotel) {
    this.editForm.update((f) => {
      const selected = f.assignedHotels.some((h) => h.propId === hotel.propId);
      return {
        ...f,
        assignedHotels: selected
          ? f.assignedHotels.filter((h) => h.propId !== hotel.propId)
          : [...f.assignedHotels, hotel],
      };
    });
  }

  removeHotel(propId: number) {
    this.editForm.update((f) => ({
      ...f,
      assignedHotels: f.assignedHotels.filter((h) => h.propId !== propId),
    }));
  }

  async requestDelete(userId: string, username: string) {
    const confirmed = await this.confirmDialog.open({
      title: 'Eliminar usuario',
      message: `¿Estás seguro de que deseas eliminar permanentemente al usuario «${username}»?`,
      details: ['Esta acción no se puede deshacer.', 'Se eliminarán todos los datos asociados a esta cuenta.'],
      variant: 'danger',
      confirmLabel: 'Eliminar',
      cancelLabel: 'Cancelar',
    });
    if (!confirmed) return;

    this.deletingId.set(userId);
    this.api
      .deleteUser(userId)
      .subscribe({
        next: (result) => {
          this.toast.success(result.message);
          this.deletingId.set(null);
          this.usersResource.reload();
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
}
