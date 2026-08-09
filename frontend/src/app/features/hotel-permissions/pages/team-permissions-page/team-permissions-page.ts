import { httpResource } from '@angular/common/http';

import { getErrorStatus, getErrorMessage } from '../../../../shared/utils/http-error.util';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import type { Observable } from 'rxjs';

import { AuthService } from '../../../../core/auth/auth.service';
import { toast } from '../../../../core/toast/toast.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';

import { AssignRoleModalComponent } from '../../partials/assign-role-modal/assign-role-modal';
import { RoleAuditModalComponent } from '../../partials/role-audit-modal/role-audit-modal';
import { RoleFormModalComponent } from '../../partials/role-form-modal/role-form-modal';
import type { HotelRoleListDto, HotelTeamDto } from '../../models/hotel-permissions.dto';
import type { HotelRole, PermissionGroup, RoleAssignment, RoleTemplate, TeamMember } from '../../models/hotel-permissions.model';
import { groupPermissions, shortPermissionLabel } from '../../models/hotel-permissions.model';
import { HotelPermissionsApiService, mapAssignment, mapHotelRole, mapMember, mapTemplate } from '../../services/hotel-permissions-api.service';

interface AssignContext {
  assignment: RoleAssignment | null;
  member: TeamMember | null;
}

/** Filtro de estado de la tabla de roles. */
type RoleStatusFilter = 'all' | 'active' | 'inactive';

/** Filtro de estado de la tabla de equipo. */
type MemberStatusFilter = 'all' | 'assigned' | 'unassigned';

interface StatusFilter<T extends string> {
  key: T;
  label: string;
  count: number;
}

@Component({
  selector: 'app-team-permissions-page',
  imports: [
    FormsModule,
    PageHeaderComponent,
    LoadingStateComponent,
    ErrorStateComponent,
    EmptyStateComponent,
    RoleFormModalComponent,
    RoleAuditModalComponent,
    AssignRoleModalComponent,
  ],
  templateUrl: './team-permissions-page.html',
  styleUrl: './team-permissions-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TeamPermissionsPageComponent {
  private readonly propCtx = inject(PropertyContextService);
  private readonly auth = inject(AuthService);
  private readonly api = inject(HotelPermissionsApiService);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly destroyRef = inject(DestroyRef);

  /** Hotel activo — drivea los dos httpResource. */
  readonly currentPropId = computed(() => this.propCtx.currentPropId());
  readonly hotelLabel = computed(() => this.propCtx.currentPropLabel());

  // ── Declarative fetching (Fase 2 endpoints) ──
  readonly rolesResource = httpResource<HotelRoleListDto>(() => {
    const pid = this.currentPropId();
    return pid ? `/api/management/hotels/${pid}/roles` : undefined;
  });

  readonly assignmentsResource = httpResource<HotelTeamDto>(() => {
    const pid = this.currentPropId();
    return pid ? `/api/management/hotels/${pid}/assignments` : undefined;
  });

  // ── Domain derived state ──
  readonly roles = computed<HotelRole[]>(() =>
    (this.rolesResource.value()?.items ?? []).map(mapHotelRole),
  );
  readonly templates = computed<RoleTemplate[]>(() =>
    (this.rolesResource.value()?.templates ?? []).map(mapTemplate),
  );
  readonly permissionCodes = computed<string[]>(() => this.rolesResource.value()?.permission_codes ?? []);

  /** Permisos del catálogo agrupados por módulo (checkboxes del modal de rol). */
  readonly permissionGroups = computed<PermissionGroup[]>(() => groupPermissions(this.permissionCodes()));

  readonly assigned = computed<RoleAssignment[]>(() =>
    (this.assignmentsResource.value()?.assigned ?? []).map(mapAssignment),
  );
  readonly unassignedStaff = computed<TeamMember[]>(() =>
    (this.assignmentsResource.value()?.unassigned_staff ?? []).map(mapMember),
  );

  readonly assignedCount = computed(() => this.assigned().length);
  readonly unassignedCount = computed(() => this.unassignedStaff().length);

  // ── Search + filter state (patrón products-list-page) ──
  // Cada tabla tiene su propio término de búsqueda para que escribir en una
  // no filtre la otra.
  readonly roleSearchTerm = signal('');
  readonly memberSearchTerm = signal('');
  readonly roleStatusFilter = signal<RoleStatusFilter>('all');
  readonly memberStatusFilter = signal<MemberStatusFilter>('all');

  /** Roles visibles según búsqueda + estado. */
  readonly filteredRoles = computed<HotelRole[]>(() => {
    const term = this.roleSearchTerm().trim().toLowerCase();
    const status = this.roleStatusFilter();
    return this.roles().filter((r) => {
      if (status === 'active' && !r.isActive) return false;
      if (status === 'inactive' && r.isActive) return false;
      if (term) {
        const haystack = `${r.displayName || r.name} ${r.name} ${r.basedOn || ''}`.toLowerCase();
        if (!haystack.includes(term)) return false;
      }
      return true;
    });
  });

  /** Miembros con rol visibles según búsqueda. */
  readonly filteredAssigned = computed<RoleAssignment[]>(() => {
    const term = this.memberSearchTerm().trim().toLowerCase();
    return this.assigned().filter((a) => {
      if (!term) return true;
      const haystack = `${a.displayName || a.username} ${a.username} ${a.roleDisplayName || a.roleName}`.toLowerCase();
      return haystack.includes(term);
    });
  });

  /** Personal sin rol visible según búsqueda. */
  readonly filteredUnassigned = computed<TeamMember[]>(() => {
    const term = this.memberSearchTerm().trim().toLowerCase();
    return this.unassignedStaff().filter((m) => {
      if (!term) return true;
      const haystack = `${m.displayName || m.username} ${m.username}`.toLowerCase();
      return haystack.includes(term);
    });
  });

  /** Chips de estado de la tabla de roles (con counts del dataset completo). */
  readonly roleStatusFilters = computed<StatusFilter<RoleStatusFilter>[]>(() => {
    const roles = this.roles();
    return [
      { key: 'all', label: 'Todos', count: roles.length },
      { key: 'active', label: 'Activos', count: roles.filter((r) => r.isActive).length },
      { key: 'inactive', label: 'Inactivos', count: roles.filter((r) => !r.isActive).length },
    ];
  });

  /** Chips de estado de la tabla de equipo. */
  readonly memberStatusFilters = computed<StatusFilter<MemberStatusFilter>[]>(() => [
    { key: 'all', label: 'Todos', count: this.assignedCount() + this.unassignedCount() },
    { key: 'assigned', label: 'Con rol', count: this.assignedCount() },
    { key: 'unassigned', label: 'Sin asignar', count: this.unassignedCount() },
  ]);

  onRoleSearchInput(value: string): void {
    this.roleSearchTerm.set(value);
  }

  onMemberSearchInput(value: string): void {
    this.memberSearchTerm.set(value);
  }

  onRoleStatusChange(key: RoleStatusFilter): void {
    this.roleStatusFilter.set(key);
  }

  onMemberStatusChange(key: MemberStatusFilter): void {
    this.memberStatusFilter.set(key);
  }

  /** El rol que tiene asignado el usuario actual (anti self-lockout en la UI). */
  readonly ownRoleId = computed<string | null>(() => {
    const username = this.auth.currentUser()?.username;
    if (!username) return null;
    return this.assigned().find((a) => a.username === username)?.roleId ?? null;
  });

  readonly noHotel = computed(() => !this.currentPropId());

  readonly viewState = computed<ViewState>(() => {
    if (this.rolesResource.isLoading() || this.assignmentsResource.isLoading()) return 'loading';
    if (this.rolesResource.error() || this.assignmentsResource.error()) return 'error';
    return 'success';
  });

  // ── Modals ──
  readonly roleModalOpen = signal(false);
  readonly editingRole = signal<HotelRole | null>(null);
  readonly assignModalOpen = signal(false);
  readonly assignContext = signal<AssignContext | null>(null);
  readonly auditRole = signal<HotelRole | null>(null);

  isOwnRole(roleId: string): boolean {
    return roleId === this.ownRoleId();
  }

  /** Abre el panel de auditoría del rol (creador, fechas, cambios de permisos). */
  openAudit(role: HotelRole): void {
    this.auditRole.set(role);
  }

  closeAudit(): void {
    this.auditRole.set(null);
  }

  /** Inicial del nombre para el avatar. */
  initial(name: string): string {
    return (name || '?').charAt(0).toUpperCase();
  }

  reload(): void {
    this.rolesResource.reload();
    this.assignmentsResource.reload();
  }

  // ── Permission chips ──
  permissionChips(role: HotelRole): { code: string; label: string }[] {
    return role.permissions.slice(0, 3).map((code) => ({ code, label: shortPermissionLabel(code) }));
  }

  // ── Role actions ──
  openCreateRole(): void {
    this.editingRole.set(null);
    this.roleModalOpen.set(true);
  }

  openEditRole(role: HotelRole): void {
    this.editingRole.set(role);
    this.roleModalOpen.set(true);
  }

  closeRoleModal(): void {
    this.roleModalOpen.set(false);
    this.editingRole.set(null);
  }

  onRoleSaved(): void {
    this.closeRoleModal();
    this.reload();
  }

  toggleRoleActive(role: HotelRole): void {
    const action = role.isActive ? 'Desactivar' : 'Activar';
    // Captura el hotel ANTES del diálogo: si el contexto cambia mientras está
    // abierto, la mutación no puede caer en otro hotel.
    const propId = this.currentPropId();
    void this.confirmDialog
      .open({
        title: `${action} rol`,
        message: `¿${action} "${role.displayName || role.name}"?`,
        confirmLabel: action,
        variant: role.isActive ? 'warning' : 'default',
      })
      .then((ok) => {
        if (!ok || !propId) return;
        this.runMutation(
          this.api.updateRole(propId, role.id, { is_active: !role.isActive }),
          () => this.reload(),
          'Error al cambiar el estado del rol.',
        );
      });
  }

  deleteRole(role: HotelRole): void {
    const propId = this.currentPropId();
    void this.confirmDialog
      .open({
        title: 'Eliminar rol',
        message: `¿Eliminar "${role.displayName || role.name}"? Solo es posible si nadie tiene asignado este rol.`,
        confirmLabel: 'Eliminar',
        variant: 'danger',
      })
      .then((ok) => {
        if (!ok || !propId) return;
        this.runMutation(
          this.api.deleteRole(propId, role.id),
          () => this.reload(),
          'Error al eliminar el rol.',
        );
      });
  }

  // ── Assignment actions ──
  openAssign(member: TeamMember): void {
    this.assignContext.set({ assignment: null, member });
    this.assignModalOpen.set(true);
  }

  openChangeRole(assignment: RoleAssignment): void {
    this.assignContext.set({ assignment, member: null });
    this.assignModalOpen.set(true);
  }

  closeAssignModal(): void {
    this.assignModalOpen.set(false);
    this.assignContext.set(null);
  }

  onAssignSaved(): void {
    this.closeAssignModal();
    this.reload();
  }

  unassign(assignment: RoleAssignment): void {
    const name = assignment.displayName || assignment.username;
    const propId = this.currentPropId();
    void this.confirmDialog
      .open({
        title: 'Desasignar miembro',
        message: `¿Quitar a "${name}" del rol "${assignment.roleDisplayName}"? Perderá el acceso a este hotel.`,
        confirmLabel: 'Desasignar',
        variant: 'danger',
      })
      .then((ok) => {
        if (!ok || !propId) return;
        this.runMutation(
          this.api.unassignUser(propId, assignment.id),
          () => this.reload(),
          'Error al desasignar al miembro.',
        );
      });
  }

  // ── Mutation plumbing with guardrail-aware errors ──
  private runMutation(obs: Observable<unknown>, onSuccess: () => void, fallback: string): void {
    obs.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        toast('Cambios guardados.', 'success');
        onSuccess();
      },
      error: (err: unknown) => this.notifyError(err, fallback),
    });
  }

  private notifyError(err: unknown, fallback: string): void {
    // getErrorMessage/getErrorStatus cubren HttpErrorResponse (tests) y
    // ApiError del interceptor (vivo).
    const msg = getErrorMessage(err) || fallback;
    // 409 = guardrail del backend (anti self-lockout / anti-lockout / duplicado /
    // rol con personal asignado). Se muestra como advertencia con el texto real.
    if (getErrorStatus(err) === 409) {
      toast(msg, 'warning');
    } else {
      toast(msg, 'error');
    }
  }
}
