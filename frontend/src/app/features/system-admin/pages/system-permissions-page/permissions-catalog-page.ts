import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { TitleCasePipe } from '@angular/common';

import { SystemPermissionsContextService } from '../../services/system-permissions-context.service';

type CrudAction = 'manage' | 'create' | 'read' | 'update' | 'delete' | 'execute';
const ACTIONS: readonly CrudAction[] = ['manage', 'create', 'read', 'update', 'delete', 'execute'];

@Component({
  selector: 'app-permissions-catalog-page',
  standalone: true,
  imports: [TitleCasePipe],
  template: `
    <section class="permissions-subpage">
      <div class="subpage-heading">
        <div>
          <span class="subpage-eyebrow">Referencia técnica</span>
          <h2>Catálogo CRUD</h2>
          <p>Recursos y acciones disponibles para asignar a los roles.</p>
        </div>
        <span class="subpage-hint"><span class="material-symbols-outlined">database</span> {{ crudMatrix().resources.length }} recursos</span>
      </div>

      @if (crudMatrix(); as matrix) {
        <div class="crud-matrix-wrap">
          <table class="crud-matrix-table">
            <thead>
              <tr>
                <th class="crud-resource-th">Recurso</th>
                @for (action of matrix.actions; track action) {
                  <th class="crud-action-th"><span class="action-header">{{ action | titlecase }}</span></th>
                }
              </tr>
            </thead>
            <tbody>
              @for (row of matrix.rows; track row.resource) {
                <tr>
                  <td class="crud-resource-td"><span class="crud-resource-name">{{ row.resource }}</span></td>
                  @for (action of matrix.actions; track action) {
                    <td class="crud-cell-td">
                      @if (row.actions[action]; as permission) {
                        <span class="crud-code-badge" [title]="permission.description">{{ permission.code }}</span>
                      } @else { <span class="crud-empty">—</span> }
                    </td>
                  }
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
export class PermissionsCatalogPageComponent {
  readonly context = inject(SystemPermissionsContextService);
  readonly crudMatrix = computed(() => {
    const vm = this.context.overviewResource.value();
    const resources = new Map<string, Partial<Record<CrudAction, { code: string; description: string }>>>();
    for (const permission of vm?.permissions || []) {
      const [resource, action] = permission.permissionCode.split('.', 2);
      if (!resource || !ACTIONS.includes(action as CrudAction)) continue;
      const row = resources.get(resource) || {};
      row[action as CrudAction] = { code: permission.permissionCode, description: permission.description };
      resources.set(resource, row);
    }
    const names = [...resources.keys()].sort();
    return { resources: names, rows: names.map((resource) => ({ resource, actions: resources.get(resource)! })), actions: ACTIONS };
  });
}
