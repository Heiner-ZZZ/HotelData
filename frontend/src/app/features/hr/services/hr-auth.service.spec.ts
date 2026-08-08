import { TestBed } from '@angular/core/testing';

import { AuthService } from '../../../core/auth/auth.service';
import { HrAuthService } from './hr-auth.service';

/**
 * Fixture de permisos granulares HR (espejo del catálogo canónico
 * server/scripts/init_security_model_ga03.py + grants de roles):
 *   - portal.read / directory.read / directory.manage / onboarding.create
 *     / shifts.read / shifts.manage
 *   - check-in/out = shifts.manage O portal.read (require_any_permission).
 */
function setup(permissionCodes: string[]) {
  TestBed.resetTestingModule();
  // Espejo de AuthService.hasPermission: el wildcard '*.*' (super_admin /
  // admin_sistema) pasa cualquier check.
  const auth = {
    hasPermission: jest.fn((code: string) => permissionCodes.includes('*.*') || permissionCodes.includes(code)),
  } as unknown as AuthService;
  TestBed.configureTestingModule({
    providers: [HrAuthService, { provide: AuthService, useValue: auth }],
  });
  return TestBed.inject(HrAuthService);
}

describe('HrAuthService', () => {
  it('otorga acceso a Mi Portal solo con hr.portal.read', () => {
    const svc = setup(['hr.portal.read']);
    expect(svc.canViewPortal()).toBe(true);
    expect(svc.canViewDirectory()).toBe(false);
    expect(svc.canManageDirectory()).toBe(false);
    expect(svc.canViewShifts()).toBe(false);
    expect(svc.canManageShifts()).toBe(false);
  });

  it('directorio: read habilita ver, manage habilita gestionar', () => {
    const svc = setup(['hr.directory.read']);
    expect(svc.canViewDirectory()).toBe(true);
    expect(svc.canManageDirectory()).toBe(false);

    const manager = setup(['hr.directory.read', 'hr.directory.manage']);
    expect(manager.canViewDirectory()).toBe(true);
    expect(manager.canManageDirectory()).toBe(true);
  });

  it('onboarding: requiere hr.onboarding.create', () => {
    const svc = setup(['hr.onboarding.create']);
    expect(svc.canOnboard()).toBe(true);
    expect(svc.canViewPortal()).toBe(false);
  });

  it('turnos: read para ver, manage para editar/eliminar', () => {
    const viewer = setup(['hr.shifts.read']);
    expect(viewer.canViewShifts()).toBe(true);
    expect(viewer.canManageShifts()).toBe(false);

    const manager = setup(['hr.shifts.read', 'hr.shifts.manage']);
    expect(manager.canViewShifts()).toBe(true);
    expect(manager.canManageShifts()).toBe(true);
  });

  it('check-in/out: shifts.manage O portal.read (require_any_permission)', () => {
    const manager = setup(['hr.shifts.manage']);
    expect(manager.canRegisterAttendance()).toBe(true);

    const empleado = setup(['hr.portal.read']);
    expect(empleado.canRegisterAttendance()).toBe(true);

    const sinAcceso = setup(['hr.directory.read']);
    expect(sinAcceso.canRegisterAttendance()).toBe(false);
  });

  it('super_admin (*.*) pasa todos los checks', () => {
    const svc = setup(['*.*']);
    expect(svc.canViewPortal()).toBe(true);
    expect(svc.canViewDirectory()).toBe(true);
    expect(svc.canManageDirectory()).toBe(true);
    expect(svc.canOnboard()).toBe(true);
    expect(svc.canViewShifts()).toBe(true);
    expect(svc.canManageShifts()).toBe(true);
    expect(svc.canRegisterAttendance()).toBe(true);
  });

  it('sin permisos no concede nada', () => {
    const svc = setup([]);
    expect(svc.canViewPortal()).toBe(false);
    expect(svc.canViewDirectory()).toBe(false);
    expect(svc.canManageDirectory()).toBe(false);
    expect(svc.canOnboard()).toBe(false);
    expect(svc.canViewShifts()).toBe(false);
    expect(svc.canManageShifts()).toBe(false);
    expect(svc.canRegisterAttendance()).toBe(false);
  });
});
