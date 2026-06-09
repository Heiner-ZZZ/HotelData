import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { RoleDetailModel, SystemPermissionsViewModel } from '../../models/system-permissions.model';
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
  readonly loadErrorMessage = signal('');
  readonly openSection = signal<string | null>(null);

  readonly editRoleName = signal<string | null>(null);
  readonly roleDetail = signal<RoleDetailModel | null>(null);
  readonly roleDetailState = signal<ViewState>('loading');
  readonly saving = signal(false);
  readonly saveMessage = signal('');

  constructor() {
    this.loadPermissions();
  }

  toggleSection(key: string) {
    this.openSection.update(v => v === key ? null : key);
  }

  openRoleEditor(roleName: string) {
    this.editRoleName.set(roleName);
    this.roleDetailState.set('loading');
    this.saveMessage.set('');
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
    this.saveMessage.set('');
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
    this.saveMessage.set('');
    this.api
      .updateRole(roleName, {
        description: detail.role.description,
        permission_codes: [...detail.role.permissionCodes],
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.saveMessage.set(res.message);
          this.saving.set(false);
          this.loadPermissions();
        },
        error: (err: ApiError) => {
          this.saveMessage.set(err.message || 'Error al guardar');
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
