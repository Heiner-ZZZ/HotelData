import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { SystemPermissionsContextService } from '../../services/system-permissions-context.service';

@Component({
  selector: 'app-permissions-roles-page',
  standalone: true,
  imports: [RouterLink],
  template: `
    <section class="permissions-subpage">
      <div class="subpage-heading">
        <div>
          <span class="subpage-eyebrow">Administración</span>
          <h2>Roles</h2>
          <p>Cada rol tiene su propia URL para compartir, revisar y editar sin perder el contexto.</p>
        </div>
      </div>

      @if (context.overviewResource.value(); as vm) {
        <div class="roles-grid">
          @for (role of vm.roles; track role.roleName) {
            <article class="role-card" [class.highlight]="role.roleName === 'admin_sistema'">
              <div class="role-card-head">
                <div class="role-card-info">
                  <h3 class="role-card-name">{{ role.roleName }}</h3>
                  <span class="role-card-desc">{{ role.description }}</span>
                </div>
                <span class="role-badge-count">{{ role.permissionCount }} permisos</span>
              </div>
              <div class="role-card-body">
                <span class="role-section-label">Accesos visibles</span>
                <div class="access-chips">
                  @for (button of role.accessButtons; track button.href) {
                    <span class="access-chip">
                      <span class="material-symbols-outlined access-chip-icon">{{ button.icon }}</span>
                      {{ button.label }}
                    </span>
                  } @empty {
                    <span class="role-card-desc">Sin accesos calculados</span>
                  }
                </div>
              </div>
              <a class="role-edit-btn" [routerLink]="[role.roleName]">
                <span class="material-symbols-outlined">edit</span>
                Abrir permisos del rol
                <span class="material-symbols-outlined role-edit-arrow">arrow_forward</span>
              </a>
            </article>
          }
        </div>
      }
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PermissionsRolesPageComponent {
  readonly context = inject(SystemPermissionsContextService);
}
