import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { SystemPermissionsContextService } from '../../services/system-permissions-context.service';
import type { SystemPermissionItem, SystemRolePermissionItem } from '../../models/system-permissions.model';

function permissionCategory(code: string): string {
  const resource = code.split('.', 1)[0] || code;
  return resource.charAt(0).toUpperCase() + resource.slice(1);
}

@Component({
  selector: 'app-permissions-matrix-page',
  standalone: true,
  imports: [RouterLink],
  template: `
    <section class="permissions-subpage">
      <div class="subpage-heading">
        <div>
          <span class="subpage-eyebrow">Vista comparativa</span>
          <h2>Matriz de permisos</h2>
          <p>Selecciona un rol para abrir su configuración en una ruta independiente.</p>
        </div>
        <span class="subpage-hint"><span class="material-symbols-outlined">touch_app</span> Filas clicables</span>
      </div>

      @if (context.overviewResource.value(); as vm) {
        <div class="matrix-wrap">
          <table class="matrix-table">
            <thead>
              <tr>
                <th class="matrix-role-th">Rol</th>
                @for (cat of permissionCategories(); track cat.key) {
                  <th class="matrix-cat-th" [title]="cat.permissions.map(p => p.permissionCode).join(', ')">
                    <span>{{ cat.key }}</span>
                    <span class="cat-count">{{ cat.permissions.length }}</span>
                  </th>
                }
                <th class="matrix-total-th">Total</th>
              </tr>
            </thead>
            <tbody>
              @for (role of vm.roles; track role.roleName) {
                <tr class="matrix-row" [routerLink]="['../roles', role.roleName]">
                  <td class="matrix-role-td">
                    <div class="matrix-role-info">
                      <span class="matrix-role-name">{{ role.roleName }}</span>
                      <span class="matrix-role-desc">{{ role.description }}</span>
                    </div>
                  </td>
                  @for (cat of permissionCategories(); track cat.key) {
                    <td class="matrix-cell">
                      @if (roleHasCategory(role, cat.key)) {
                        <span class="matrix-dot matrix-dot--active" title="Tiene permisos en {{ cat.key }}"></span>
                      } @else {
                        <span class="matrix-dot matrix-dot--empty"></span>
                      }
                    </td>
                  }
                  <td class="matrix-total-td"><span class="total-badge">{{ role.permissionCount }}</span></td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PermissionsMatrixPageComponent {
  readonly context = inject(SystemPermissionsContextService);

  readonly permissionCategories = computed(() => {
    const vm = this.context.overviewResource.value();
    if (!vm) return [];
    const categories: { key: string; permissions: SystemPermissionItem[] }[] = [];
    const byKey = new Map<string, SystemPermissionItem[]>();
    for (const permission of vm.permissions) {
      const key = permissionCategory(permission.permissionCode);
      const list = byKey.get(key) || [];
      list.push(permission);
      byKey.set(key, list);
    }
    for (const [key, permissions] of byKey) categories.push({ key, permissions });
    return categories;
  });

  roleHasCategory(role: SystemRolePermissionItem, categoryKey: string): boolean {
    return role.permissionCodes.some((code) => permissionCategory(code) === categoryKey);
  }
}
