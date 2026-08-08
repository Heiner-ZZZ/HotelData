import { computed, inject, Injectable } from '@angular/core';

import { AuthService } from '../../../core/auth/auth.service';
import { HR_PORTAL_READ, HR_DIRECTORY_READ, HR_DIRECTORY_MANAGE, HR_ONBOARDING_CREATE, HR_SHIFTS_READ, HR_SHIFTS_MANAGE } from '../../../core/auth/permission.constants';

/**
 * Centralized computed signals for HR feature permission gating.
 *
 * Espejo del desglose granular del backend (server/src/app/modules/hr/routes.py
 * + catálogo canónico init_security_model_ga03.py). Cada interfaz RRHH tiene
 * su propio permiso:
 *
 *   - Mi Portal      → hr.portal.read
 *   - Directorio     → hr.directory.read (ver) / hr.directory.manage (gestionar)
 *   - Onboarding     → hr.onboarding.create
 *   - Turnos         → hr.shifts.read (ver) / hr.shifts.manage (gestionar)
 *   - Check-in/out   → hr.shifts.manage O hr.portal.read (require_any_permission)
 *
 * Inject this service in any HR component that needs to gate UI elements by
 * interface — the computed signals stay consistent with the backend route
 * gates. Reads ``AuthService.hasPermission()``, que lee el signal reactivo de
 * ``permissionCodes``, así que los computeds se recalculan al loguear/desloguear.
 */
@Injectable({ providedIn: 'root' })
export class HrAuthService {
  private readonly auth = inject(AuthService);

  /** Mi Portal (auto-servicio del empleado): hr.portal.read */
  readonly canViewPortal = computed(() => this.auth.hasPermission(HR_PORTAL_READ));

  /** Directorio: ver empleados/departamentos/documentos (hr.directory.read) */
  readonly canViewDirectory = computed(() => this.auth.hasPermission(HR_DIRECTORY_READ));

  /** Directorio: crear/editar/eliminar (hr.directory.manage) */
  readonly canManageDirectory = computed(() => this.auth.hasPermission(HR_DIRECTORY_MANAGE));

  /** Onboarding: crear empleados + transferir permisos (hr.onboarding.create) */
  readonly canOnboard = computed(() => this.auth.hasPermission(HR_ONBOARDING_CREATE));

  /** Turnos: ver horarios (hr.shifts.read) */
  readonly canViewShifts = computed(() => this.auth.hasPermission(HR_SHIFTS_READ));

  /** Turnos: crear/editar/eliminar/check-in/check-out (hr.shifts.manage) */
  readonly canManageShifts = computed(() => this.auth.hasPermission(HR_SHIFTS_MANAGE));

  /**
   * Registrar asistencia (check-in/check-out): el gerente con
   * hr.shifts.manage O el empleado desde su Mi Portal con hr.portal.read —
   * espejo del require_any_permission("hr.shifts.manage", "hr.portal.read").
   */
  readonly canRegisterAttendance = computed(
    () => this.auth.hasPermission(HR_SHIFTS_MANAGE) || this.auth.hasPermission(HR_PORTAL_READ),
  );
}
