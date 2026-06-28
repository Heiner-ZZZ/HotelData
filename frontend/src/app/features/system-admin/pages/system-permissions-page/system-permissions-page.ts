import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { ToastService } from '../../../../shared/services/toast.service';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { RoleDetailModel, SystemPermissionItem, SystemPermissionsViewModel, SystemRolePermissionItem } from '../../models/system-permissions.model';
import { SystemPermissionsApiService } from '../../services/system-permissions-api.service';

/** A permission category derived from the code prefix (e.g. 'view_', 'edit_', 'manage_', 'delete_'). */
function _permissionCategory(code: string): string {
  const prefix = code.split('_')[0] || code;
  return prefix.charAt(0).toUpperCase() + prefix.slice(1);
}

@Component({
  selector: 'app-system-permissions-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
  ],
  templateUrl: './system-permissions-page.html',
  styleUrl: './system-permissions-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SystemPermissionsPageComponent {
  private readonly api = inject(SystemPermissionsApiService);
  private readonly toast = inject(ToastService);
  private readonly destroyRef = inject(DestroyRef);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<SystemPermissionsViewModel | null>(null);
  readonly loadErrorMessage = signal('');

  // ── Role editor state ──
  readonly editRoleName = signal<string | null>(null);
  readonly roleDetail = signal<RoleDetailModel | null>(null);
  readonly roleDetailState = signal<ViewState>('loading');
  readonly saving = signal(false);

  // ── Tab selection: 'matrix' | 'roles' | 'catalog' ──
  readonly activeTab = signal<'matrix' | 'roles' | 'catalog'>('matrix');

  // ── Permission categories for the matrix view ──
  readonly permissionCategories = computed(() => {
    const vm = this.viewModel();
    if (!vm) return [];
    const seen = new Set<string>();
    const cats: Array<{ key: string; permissions: SystemPermissionItem[] }> = [];
    for (const perm of vm.permissions) {
      const cat = _permissionCategory(perm.permissionCode);
      if (!seen.has(cat)) {
        seen.add(cat);
        cats.push({ key: cat, permissions: [perm] });
      } else {
        const existing = cats.find((c) => c.key === cat);
        if (existing) existing.permissions.push(perm);
      }
    }
    return cats;
  });

  /** Whether a role has at least one permission in a category */
  roleHasCategory(role: SystemRolePermissionItem, categoryKey: string): boolean {
    return role.permissionCodes.some(
      (code) => _permissionCategory(code) === categoryKey
    );
  }

  /** Expose permissionCategory to template */
  readonly permissionCategory = _permissionCategory;

  constructor() {
    this.loadPermissions();
  }

  setTab(tab: 'matrix' | 'roles' | 'catalog') {
    this.activeTab.set(tab);
  }

  openRoleEditor(roleName: string) {
    this.editRoleName.set(roleName);
    this.roleDetailState.set('loading');
    this.roleDetail.set(null);
    this.api
      .getRoleDetail(roleName)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (detail) => {
          this.roleDetail.set(detail);
          this.roleDetailState.set('success');
        },
        error: () => {
          this.roleDetailState.set('error');
        },
      });
  }

  closeRoleEditor() {
    this.editRoleName.set(null);
    this.roleDetail.set(null);
  }

  togglePermission(code: string) {
    const detail = this.roleDetail();
    if (!detail) return;
    const codes = detail.role.permissionCodes;
    const idx = codes.indexOf(code);
    if (idx >= 0) {
      codes.splice(idx, 1);
    } else {
      codes.push(code);
    }
    this.roleDetail.set({ ...detail });
  }

  saveRole() {
    const detail = this.roleDetail();
    const roleName = this.editRoleName();
    if (!detail || !roleName) return;
    this.saving.set(true);
    this.api
      .updateRole(roleName, {
        description: detail.role.description,
        permission_codes: [...detail.role.permissionCodes],
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.toast.success(res.message);
          this.saving.set(false);
          this.loadPermissions();
        },
        error: (err: ApiError) => {
          this.toast.error(err.message || 'Error al guardar los permisos del rol.');
          this.saving.set(false);
        },
      });
  }

  private loadPermissions() {
    this.viewState.set('loading');
    this.loadErrorMessage.set('');
    this.api
      .getPermissionsOverview()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (vm) => {
          this.viewModel.set(vm);
          this.viewState.set(vm.roles.length || vm.permissions.length ? 'success' : 'empty');
        },
        error: (error: ApiError) => {
          this.loadErrorMessage.set(error.message || 'No fue posible cargar los permisos.');
          this.viewState.set('error');
        },
      });
  }
}
