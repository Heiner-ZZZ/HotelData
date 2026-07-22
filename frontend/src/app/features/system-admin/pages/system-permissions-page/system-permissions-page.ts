import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';

import { ConfirmDialogComponent } from '../../../../shared/ui/confirm-dialog/confirm-dialog.component';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { ToastService } from '../../../../shared/services/toast.service';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { RoleDetailModel, SystemPermissionItem, SystemPermissionsViewModel, SystemRolePermissionItem } from '../../models/system-permissions.model';
import type { SystemPermissionsResponseDto } from '../../models/system-permissions.dto';
import { SystemPermissionsApiService } from '../../services/system-permissions-api.service';
import { mapSystemPermissionsResponse } from '../../mappers/system-permissions.mapper';

/** A permission category derived from the resource name (part before the first dot). */
function _permissionCategory(code: string): string {
  const parsed = _parseCode(code);
  const resource = parsed?.resource || code;
  return resource.charAt(0).toUpperCase() + resource.slice(1);
}

/** Parse "resource.action" into { resource, action }. */
function _parseCode(code: string): { resource: string; action: string } | null {
  const dot = code.indexOf('.');
  if (dot === -1) return null;
  return { resource: code.substring(0, dot), action: code.substring(dot + 1) };
}

const ACTION_ORDER = ['manage', 'create', 'read', 'update', 'delete', 'execute'] as const;
type CrudAction = typeof ACTION_ORDER[number];

interface CrudMatrixRow {
  resource: string;
  actions: Partial<Record<CrudAction, { code: string; description: string }>>;
}

interface CrudMatrixViewModel {
  resources: string[];
  rows: CrudMatrixRow[];
  actions: readonly CrudAction[];
}

@Component({
  selector: 'app-system-permissions-page',
  imports: [
    ConfirmDialogComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    TitleCasePipe,
  ],
  templateUrl: './system-permissions-page.html',
  styleUrl: './system-permissions-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SystemPermissionsPageComponent {
  private readonly api = inject(SystemPermissionsApiService);
  private readonly toast = inject(ToastService);
  private readonly confirmDialog = inject(ConfirmDialogService);

  readonly permissionsResource = httpResource<SystemPermissionsViewModel>(() => '/api/admin/permissions', {
    parse: (dto) => mapSystemPermissionsResponse(dto as SystemPermissionsResponseDto),
  });

  readonly viewState = computed<ViewState>(() => {
    if (this.permissionsResource.isLoading()) return 'loading';
    if (this.permissionsResource.error()) return 'error';
    const vm = this.permissionsResource.value();
    if (!vm) return 'loading';
    return vm.roles.length || vm.permissions.length ? 'success' : 'empty';
  });

  readonly loadErrorMessage = computed(() => {
    const err = this.permissionsResource.error();
    return (err as unknown as ApiError)?.message || '';
  });

  // ── Role editor state ──
  readonly editRoleName = signal<string | null>(null);
  readonly roleDetail = signal<RoleDetailModel | null>(null);
  readonly roleDetailState = signal<ViewState>('loading');
  readonly saving = signal(false);

  // ── Tab selection: 'matrix' | 'roles' | 'catalog' ──
  readonly activeTab = signal<'matrix' | 'roles' | 'catalog'>('matrix');

  // ── Permission categories for the matrix view ──
  readonly permissionCategories = computed(() => {
    const vm = this.permissionsResource.value();
    if (!vm) return [];
    const seen = new Set<string>();
    const cats: { key: string; permissions: SystemPermissionItem[] }[] = [];
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

  // ── CRUD Matrix: resource × action grid ──
  readonly crudMatrix = computed<CrudMatrixViewModel>(() => {
    const vm = this.permissionsResource.value();
    if (!vm) return { resources: [], rows: [], actions: ACTION_ORDER };

    const resources = new Map<string, CrudMatrixRow['actions']>();
    for (const perm of vm.permissions) {
      const parsed = _parseCode(perm.permissionCode);
      if (!parsed) continue;
      if (!ACTION_ORDER.includes(parsed.action as CrudAction)) continue;
      if (!resources.has(parsed.resource)) {
        resources.set(parsed.resource, {});
      }
      resources.get(parsed.resource)![parsed.action as CrudAction] = {
        code: perm.permissionCode,
        description: perm.description,
      };
    }

    // Sort resources alphabetically
    const sortedResources = [...resources.keys()].sort();
    const rows: CrudMatrixRow[] = sortedResources.map(resource => ({
      resource,
      actions: resources.get(resource)!,
    }));

    return { resources: sortedResources, rows, actions: ACTION_ORDER };
  });

  /** Toggle all CRUD actions for a resource (when manage checkbox is clicked). */
  toggleResourceActions(resource: string) {
    const detail = this.roleDetail();
    const matrix = this.crudMatrix();
    if (!detail || !matrix) return;

    const row = matrix.rows.find(r => r.resource === resource);
    if (!row) return;

    const allActionCodes = Object.values(row.actions)
      .filter((a): a is NonNullable<typeof a> => !!a)
      .map(a => a.code);

    // If all actions are already selected, deselect them; otherwise select all
    const allSelected = allActionCodes.every(c => detail.role.permissionCodes.includes(c));
    const codes = detail.role.permissionCodes;

    if (allSelected) {
      // Deselect all
      for (const c of allActionCodes) {
        const idx = codes.indexOf(c);
        if (idx >= 0) codes.splice(idx, 1);
      }
    } else {
      // Select all missing ones
      for (const c of allActionCodes) {
        if (!codes.includes(c)) codes.push(c);
      }
    }
    this.roleDetail.set({ ...detail });
  }

  /** Whether all CRUD actions for a resource are selected (for the manage checkbox). */
  isResourceFullySelected(resource: string): boolean {
    const detail = this.roleDetail();
    const matrix = this.crudMatrix();
    if (!detail || !matrix) return false;

    const row = matrix.rows.find(r => r.resource === resource);
    if (!row) return false;

    const allActionCodes = Object.values(row.actions)
      .filter((a): a is NonNullable<typeof a> => !!a)
      .map(a => a.code);

    return allActionCodes.length > 0 && allActionCodes.every(c => detail.role.permissionCodes.includes(c));
  }

  /** Whether a resource is partially selected (some but not all actions). */
  isResourcePartiallySelected(resource: string): boolean {
    const detail = this.roleDetail();
    const matrix = this.crudMatrix();
    if (!detail || !matrix) return false;

    const row = matrix.rows.find(r => r.resource === resource);
    if (!row) return false;

    const allActionCodes = Object.values(row.actions)
      .filter((a): a is NonNullable<typeof a> => !!a)
      .map(a => a.code);

    const selectedCount = allActionCodes.filter(c => detail.role.permissionCodes.includes(c)).length;
    return selectedCount > 0 && selectedCount < allActionCodes.length;
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

  async saveRole() {
    const detail = this.roleDetail();
    const roleName = this.editRoleName();
    if (!detail || !roleName) return;

    const confirmed = await this.confirmDialog.open({
      title: 'Guardar cambios del rol',
      message: `¿Confirmas la actualización de permisos para el rol «${roleName}»?`,
      details: [
        `${detail.role.permissionCodes.length} permisos seleccionados`,
        'Los cambios afectarán a todos los usuarios con este rol.',
      ],
      variant: 'warning',
      confirmLabel: 'Guardar cambios',
      cancelLabel: 'Cancelar',
    });
    if (!confirmed) return;

    this.saving.set(true);
    this.api
      .updateRole(roleName, {
        description: detail.role.description,
        permission_codes: [...detail.role.permissionCodes],
      })
      .subscribe({
        next: (res) => {
          this.toast.success(res.message);
          this.saving.set(false);
          this.permissionsResource.reload();
        },
        error: (err: ApiError) => {
          this.toast.error(err.message || 'Error al guardar los permisos del rol.');
          this.saving.set(false);
        },
      });
  }
}
