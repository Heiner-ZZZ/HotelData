import { pickFirstAccessibleManagementHref } from './management-redirect';

describe('pickFirstAccessibleManagementHref — redirección dinámica de /management (TDD)', () => {
  // Códigos de housekeeping canónico (sin reports.strategic.read)
  const HOUSEKEEPING_CODES = [
    'dashboard.read',
    'housekeeping.read',
    'housekeeping.update',
    'maintenance.read',
    'inventory.read',
    'rooms.read',
    'hr.read',
    'hr.portal.read',
    'hr.directory.read',
    'lost-found.read',
    'lost-found.update',
    'reports.tactical.read',
    'reports.housekeeping.dashboard.read',
    'reports.housekeeping.operations.read',
    'reports.housekeeping.matrix.read',
  ];

  const MAINTENANCE_CODES = [
    'dashboard.read',
    'housekeeping.read',
    'housekeeping.update',
    'maintenance.manage',
    'inventory.read',
    'hr.read',
    'hr.portal.read',
    'hr.directory.read',
    'lost-found.read',
    'lost-found.update',
    'reports.tactical.read',
    'reports.housekeeping.operations.read',
    'reports.housekeeping.matrix.read',
  ];

  const GERENTE_CODES = [
    'dashboard.read',
    'reports.strategic.read',
    'reports.tactical.read',
    'reports.download',
    'reservations.manage',
    'housekeeping.read',
  ];

  it('para housekeeping sin reports.strategic.read NO redirige a informes-estrategicos/h01', () => {
    const href = pickFirstAccessibleManagementHref(HOUSEKEEPING_CODES, 'housekeeping');
    expect(href).not.toContain('informes-estrategicos');
    expect(href.startsWith('/management')).toBe(true);
  });

  it('para housekeeping redirige a una ruta de housekeeping/hr que sí tiene permiso (dinámico, no estático)', () => {
    const href = pickFirstAccessibleManagementHref(HOUSEKEEPING_CODES, 'housekeeping');
    // Debe ser una de las rutas que housekeeping puede abrir, no un fallback genérico
    const allowed = [
      '/management/housekeeping',
      '/management/housekeeping/dashboard',
      '/management/housekeeping/operations',
      '/management/housekeeping/matrix',
      '/management/hr/my-portal',
      '/management/availability',
    ];
    expect(allowed).toContain(href);
  });

  it('para maintenance (Carlos) tampoco redirige a estratégico y elige su primera ruta permitida', () => {
    const href = pickFirstAccessibleManagementHref(MAINTENANCE_CODES, 'maintenance');
    expect(href).not.toContain('informes-estrategicos');
    expect(href.startsWith('/management')).toBe(true);
  });

  it('para gerente_hotel con reports.strategic.read sí puede ir a h01', () => {
    const href = pickFirstAccessibleManagementHref(GERENTE_CODES, 'gerente_hotel');
    expect(href).toBe('/management/informes-estrategicos/h01');
  });

  it('para super_admin con wildcard *.* va a h01 (tiene todo)', () => {
    const href = pickFirstAccessibleManagementHref(['*.*'], 'super_admin');
    expect(href).toBe('/management/informes-estrategicos/h01');
  });

  it('si no tiene ningún permiso de management cae a /search (fallback público)', () => {
    const href = pickFirstAccessibleManagementHref(['search.read'], 'cliente');
    expect(href).toBe('/search');
  });
});
