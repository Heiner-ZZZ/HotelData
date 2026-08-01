import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { takeUntilDestroyed, toObservable, toSignal } from '@angular/core/rxjs-interop';
import { debounceTime, distinctUntilChanged, switchMap } from 'rxjs';

import { ConfirmDialogComponent } from '../../../../shared/ui/confirm-dialog/confirm-dialog.component';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { ToastService } from '../../../../shared/services/toast.service';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { RoleDetailResponseDto } from '../../models/system-permissions.dto';
import type { RoleDetailModel } from '../../models/system-permissions.model';
import { mapRoleDetailResponse } from '../../mappers/system-permissions.mapper';
import { SystemPermissionsApiService } from '../../services/system-permissions-api.service';
import { SystemPermissionsContextService } from '../../services/system-permissions-context.service';

type CrudAction = 'manage' | 'create' | 'read' | 'update' | 'delete' | 'execute';
const ACTIONS: readonly CrudAction[] = ['manage', 'create', 'read', 'update', 'delete', 'execute'];

@Component({
  selector: 'app-role-permissions-page',
  standalone: true,
  imports: [ConfirmDialogComponent, ErrorStateComponent, LoadingStateComponent, RouterLink],
  template: `
    <app-confirm-dialog />
    <section class="permissions-subpage role-detail-page">
      @if (detailResource.isLoading()) {
        <app-loading-state label="Cargando detalle del rol..." />
      } @else if (detailResource.error()) {
        <app-error-state title="No fue posible cargar el rol" description="Revisa el nombre del rol o vuelve a la lista de roles." />
      } @else if (detailResource.value(); as detail) {
        <div class="role-detail-header">
          <div>
            <a class="back-link" routerLink="../">
              <span class="material-symbols-outlined">arrow_back</span> Volver a roles
            </a>
            <div class="role-detail-title-row">
              <span class="editor-badge">{{ detail.role.roleName }}</span>
              <span class="editor-subtitle">{{ selectedCodes().length }} permisos asignados</span>
            </div>
          </div>
          <button type="button" class="btn btn-sm btn-danger" (click)="closeEditor()">
            <span class="material-symbols-outlined">close</span> Cerrar
          </button>
        </div>

        <div class="editor-body">
          <div class="editor-perms">
            <div class="field">
              <label class="field-label" for="role-description">Descripción del rol</label>
              <textarea id="role-description" class="field-input" [value]="description()" (input)="description.set($any($event.target).value)" rows="2"></textarea>
            </div>

            <div class="editor-perms-header">
              <span class="field-label">Permisos — Matriz CRUD</span>
              <span class="perm-count">{{ selectedCodes().length }} / {{ detail.permissions.length }} seleccionados</span>
            </div>

            <div class="crud-matrix-wrap">
              <table class="crud-matrix-table">
                <thead>
                  <tr>
                    <th class="crud-resource-th">Recurso</th>
                    @for (action of actions; track action) { <th class="crud-action-th">{{ action }}</th> }
                  </tr>
                </thead>
                <tbody>
                  @for (row of crudRows(); track row.resource) {
                    <tr class="crud-row" [class.crud-row--partial]="isPartiallySelected(row.resource)">
                      <td class="crud-resource-td"><span class="crud-resource-name">{{ row.resource }}</span></td>
                      <td class="crud-check-td">
                        @if (row.actions.manage) {
                          <label class="crud-check" [class.crud-check--partial]="isPartiallySelected(row.resource)">
                            <input type="checkbox" [checked]="isFullySelected(row.resource)" [indeterminate]="isPartiallySelected(row.resource)" [disabled]="!hasReadPermission(row.resource)" (change)="toggleResource(row.resource)" />
                            <span class="crud-check-label">manage</span>
                          </label>
                        } @else { <span class="crud-empty">—</span> }
                      </td>
                      @for (action of actions; track action) {
                        @if (action !== 'manage') {
                          <td class="crud-check-td">
                            @if (row.actions[action]; as permission) {
                              <label class="crud-check">
                                <input type="checkbox" [checked]="selectedCodes().includes(permission.code)" [disabled]="action !== 'read' && !hasReadPermission(row.resource)" (change)="togglePermission(permission.code)" />
                              </label>
                            } @else { <span class="crud-empty">—</span> }
                          </td>
                        }
                      }
                    </tr>
                  }
                </tbody>
              </table>
            </div>

            <div class="editor-actions">
              <button type="button" class="btn btn-primary" [disabled]="saving()" (click)="saveRole()">
                @if (saving()) { <span class="material-symbols-outlined spinning">refresh</span> Guardando… }
                @else { <span class="material-symbols-outlined">save</span> Guardar cambios }
              </button>
              @if (previewing()) { <span class="preview-sync"><span class="material-symbols-outlined spinning">sync</span> Actualizando vista previa…</span> }
            </div>
          </div>

          <aside class="editor-preview">
            <div class="preview-header">
              <span class="material-symbols-outlined preview-header-icon">visibility</span>
              <span>Vista previa de navegación</span>
            </div>
            <p class="preview-desc">Menú que verá este rol según los permisos seleccionados. Se actualiza sin guardar.</p>
            <div class="nav-preview-list">
              @for (item of navigationCatalog(); track item.permissionId ?? (item.href + '|' + item.label + '|' + item.icon)) {
                <div class="nav-item" [class.visible]="item.visible" [class.hidden]="!item.visible">
                  <span class="nav-icon material-symbols-outlined">{{ item.icon }}</span>
                  <span class="nav-label">{{ item.label }}</span>
                  <span class="nav-badge" [class.visible-badge]="item.visible" [class.hidden-badge]="!item.visible">{{ item.visible ? 'Visible' : 'Oculto' }}</span>
                </div>
              } @empty {
                <span class="role-card-desc">No hay elementos de navegación registrados.</span>
              }
            </div>
          </aside>
        </div>
      }
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RolePermissionsPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(SystemPermissionsApiService);
  private readonly context = inject(SystemPermissionsContextService);
  private readonly toast = inject(ToastService);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly destroyRef = inject(DestroyRef);

  readonly actions = ACTIONS;
  readonly roleName = toSignal(this.route.paramMap, { initialValue: this.route.snapshot.paramMap });
  readonly roleParam = computed(() => this.roleName().get('roleName') || '');
  readonly detailResource = httpResource<RoleDetailModel>(() => {
    const roleName = this.roleParam();
    return roleName ? `/api/admin/permissions/roles/${encodeURIComponent(roleName)}` : undefined;
  }, { parse: (dto) => mapRoleDetailResponse(dto as RoleDetailResponseDto) });

  readonly selectedCodes = signal<string[]>([]);
  readonly description = signal('');
  readonly navigationCatalog = signal<RoleDetailModel['role']['navigationCatalog']>([]);
  readonly previewCodes = signal<string[] | null>(null);
  readonly previewing = signal(false);
  readonly saving = signal(false);

  readonly crudRows = computed(() => {
    const permissions = this.detailResource.value()?.permissions || [];
    const resources = new Map<string, Partial<Record<CrudAction, { code: string; description: string }>>>();
    for (const permission of permissions) {
      const [resource, action] = permission.permissionCode.split('.', 2);
      if (!resource || !ACTIONS.includes(action as CrudAction)) continue;
      const row = resources.get(resource) || {};
      row[action as CrudAction] = { code: permission.permissionCode, description: permission.description };
      resources.set(resource, row);
    }
    const names = [...resources.keys()].sort();
    return names.map((resource) => ({ resource, actions: resources.get(resource)! }));
  });

  constructor() {
    effect(() => {
      const detail = this.detailResource.value();
      if (!detail) return;
      this.selectedCodes.set(this.withReadDependencies(detail.role.permissionCodes));
      this.description.set(detail.role.description);
      this.navigationCatalog.set(detail.role.navigationCatalog);
    }, { allowSignalWrites: true });

    toObservable(this.previewCodes).pipe(
      distinctUntilChanged((a, b) => (a || []).join('|') === (b || []).join('|')),
      debounceTime(120),
      switchMap((permissionCodes) => {
        if (!permissionCodes) return [];
        this.previewing.set(true);
        return this.api.previewNavigation(permissionCodes);
      }),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (items) => {
        this.navigationCatalog.set(items);
        this.previewing.set(false);
      },
      error: () => this.previewing.set(false),
    });
  }

  isFullySelected(resource: string): boolean {
    const row = this.crudRows().find((item) => item.resource === resource);
    const codes = Object.values(row?.actions || {}).filter(Boolean).map((item) => item!.code);
    return codes.length > 0 && codes.every((code) => this.selectedCodes().includes(code));
  }

  isPartiallySelected(resource: string): boolean {
    const row = this.crudRows().find((item) => item.resource === resource);
    const codes = Object.values(row?.actions || {}).filter(Boolean).map((item) => item!.code);
    const count = codes.filter((code) => this.selectedCodes().includes(code)).length;
    return count > 0 && count < codes.length;
  }

  hasReadPermission(resource: string): boolean {
    return Boolean(this.crudRows().find((item) => item.resource === resource)?.actions.read);
  }

  toggleResource(resource: string): void {
    const wasFullySelected = this.isFullySelected(resource);
    const row = this.crudRows().find((item) => item.resource === resource);
    if (!row || !this.hasReadPermission(resource)) {
      if (row && !this.hasReadPermission(resource)) {
        this.toast.warning(`No se puede asignar acciones de ${resource}: el catálogo no tiene ${resource}.read.`);
      }
      return;
    }
    const codes = Object.values(row.actions).filter(Boolean).map((item) => item!.code);
    const selected = new Set(this.selectedCodes());
    if (codes.every((code) => selected.has(code))) {
      codes.forEach((code) => selected.delete(code));
    } else {
      codes.forEach((code) => selected.add(code));
      const readCode = row.actions.read?.code;
      if (readCode) selected.add(readCode);
    }
    this.selectedCodes.set([...selected]);
    if (wasFullySelected || this.isFullySelected(resource)) this.requestPreview();
  }

  togglePermission(code: string): void {
    const [resource, action] = code.split('.', 2);
    if (!resource || !action) return;

    const wasFullySelected = this.isFullySelected(resource);
    const selected = new Set(this.selectedCodes());
    if (selected.has(code)) {
      if (action === 'read' && this.hasOtherSelectedAction(resource)) {
        this.toast.warning(`El permiso ${resource}.read es obligatorio mientras haya otras acciones activas.`);
        return;
      }
      selected.delete(code);
    } else {
      if (action !== 'read' && !this.hasReadPermission(resource)) {
        this.toast.warning(`Primero debe existir ${resource}.read para activar ${action}.`);
        return;
      }
      selected.add(code);
      if (action !== 'read') {
        const readCode = this.crudRows().find((item) => item.resource === resource)?.actions.read?.code;
        if (readCode) selected.add(readCode);
      }
    }
    this.selectedCodes.set([...selected]);
    if (wasFullySelected || this.isFullySelected(resource)) this.requestPreview();
  }

  private hasOtherSelectedAction(resource: string): boolean {
    const prefix = `${resource}.`;
    return this.selectedCodes().some((selectedCode) =>
      selectedCode.startsWith(prefix) && selectedCode !== `${resource}.read`,
    );
  }

  private withReadDependencies(codes: string[]): string[] {
    const normalized = new Set(codes);
    for (const code of codes) {
      const [resource, action] = code.split('.', 2);
      if (!resource || !action || action === 'read') continue;
      const readCode = this.crudRows().find((row) => row.resource === resource)?.actions.read?.code;
      if (readCode) normalized.add(readCode);
    }
    return [...normalized];
  }

  private requestPreview(): void {
    this.previewCodes.set([...this.selectedCodes()]);
  }

  async saveRole(): Promise<void> {
    const roleName = this.roleParam();
    if (!roleName || roleName === 'super_admin') return;
    const confirmed = await this.confirmDialog.open({
      title: 'Guardar cambios del rol',
      message: `¿Confirmas la actualización de permisos para el rol «${roleName}»?`,
      details: [`${this.selectedCodes().length} permisos seleccionados`, 'Los cambios afectarán a todos los usuarios con este rol.'],
      variant: 'warning',
      confirmLabel: 'Guardar cambios',
      cancelLabel: 'Cancelar',
    });
    if (!confirmed) return;
    this.saving.set(true);
    this.api.updateRole(roleName, { description: this.description(), permission_codes: [...this.selectedCodes()] }).subscribe({
      next: (res) => {
        this.toast.success(res.message);
        this.saving.set(false);
        this.context.overviewResource.reload();
        this.detailResource.reload();
      },
      error: (err: ApiError) => {
        this.toast.error(err.message || 'Error al guardar los permisos del rol.');
        this.saving.set(false);
      },
    });
  }

  closeEditor(): void {
    void this.router.navigate(['/system/permissions/roles']);
  }
}
