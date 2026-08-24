import type { Router } from '@angular/router';

import type { AuthState } from './auth.models';
import { isRouteAccessible, pickAccessibleDestination } from './route-access';

/** Mismos códigos que GUEST_PERMISSION_CODES (server/src/app/security/permissions.py). */
const GUEST_CODES = [
  'account.manage',
  'account.read',
  'account.update',
  'account.bookings.read',
  'search.manage',
  'search.read',
];

const MANAGEMENT_ROLES = [
  'super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'revenue_manager',
  'marketing_hotelero', 'operador_datos', 'auditor_datos', 'maintenance', 'recepcionista',
  'housekeeping', 'concierge',
];

const ACCOUNT_ROLES = ['super_admin', 'admin_sistema', 'cliente', ...MANAGEMENT_ROLES];

/** Mismo data de los shells reales en app.routes.ts (los children públicos
 *  como /search NO tienen entrada top-level — se prueban por ausencia). */
const SHELL_ROUTES = [
  { path: 'account', data: { requiredPermission: 'account.read', allowedRoles: ACCOUNT_ROLES } },
  { path: 'management', data: { requiredPermission: 'dashboard.read', allowedRoles: MANAGEMENT_ROLES } },
  { path: 'system', data: { requiredPermission: 'users.read', allowedRoles: ['super_admin', 'admin_sistema', 'operador_datos', 'auditor_datos'] } },
] as unknown as Router['config'];

function guestState(overrides: Partial<AuthState> = {}): AuthState {
  return {
    authenticated: true,
    user: {
      username: 'Horuz',
      email: 'horuz@hoteldata.local',
      displayName: 'Horuz',
      primaryRole: 'cliente',
      primaryRoleId: '',
      isActive: true,
      avatarUrl: '',
    },
    session: null,
    homeHref: '/search',
    permissionCodes: [...GUEST_CODES],
    ...overrides,
  };
}

function routerWith(config: Router['config']): Pick<Router, 'config'> {
  return { config };
}

describe('isRouteAccessible', () => {
  const router = routerWith(SHELL_ROUTES);
  const guest = guestState();

  it('permite al huésped su propio auto-servicio (/account/*)', () => {
    expect(isRouteAccessible(router, '/account/bookings', guest)).toBe(true);
  });

  it('deniega al huésped las secciones de gestión (/management)', () => {
    expect(isRouteAccessible(router, '/management', guest)).toBe(false);
    expect(isRouteAccessible(router, '/management/properties', guest)).toBe(false);
  });

  it('deniega al huésped las secciones de plataforma (/system)', () => {
    expect(isRouteAccessible(router, '/system/users', guest)).toBe(false);
  });

  it('trata rutas públicas sin entrada top-level (children del public-shell) como accesibles', () => {
    expect(isRouteAccessible(router, '/search', guest)).toBe(true);
    expect(isRouteAccessible(router, '/hotels/detalle', guest)).toBe(true);
    expect(isRouteAccessible(router, '/welcome', guest)).toBe(true);
  });

  it('ignora query string y hash al hacer el match', () => {
    expect(isRouteAccessible(router, '/management?tab=pricing', guest)).toBe(false);
    expect(isRouteAccessible(router, '/account/bookings#resumen', guest)).toBe(true);
  });

  it('concede acceso por wildcard *.* (super_admin)', () => {
    const admin = guestState({
      user: { ...guest.user!, primaryRole: 'super_admin' },
      permissionCodes: ['*.*'],
    });
    expect(isRouteAccessible(router, '/system/users', admin)).toBe(true);
    expect(isRouteAccessible(router, '/management', admin)).toBe(true);
  });

  it('concede acceso por rol aunque falte el permiso (backward-compat del guard)', () => {
    const gerente = guestState({
      user: { ...guest.user!, primaryRole: 'gerente_hotel' },
      permissionCodes: [],
    });
    expect(isRouteAccessible(router, '/management', gerente)).toBe(true);
  });

  it('ruta raíz vacía → accesible', () => {
    expect(isRouteAccessible(router, '', guest)).toBe(true);
  });

  it('espeja el fallback del guard para rutas con solo requiredPermission (sin allowedRoles)', () => {
    const routerPermOnly = routerWith([
      { path: 'informes-estrategicos', data: { requiredPermission: 'reports.strategic.portfolio.read' } },
    ] as unknown as Router['config']);
    // roleGuard: si allowedRoles está vacío, hasAllowedRole devuelve true →
    // cualquier usuario autenticado pasa. El resolver debe replicarlo para no
    // divergir del guard.
    expect(isRouteAccessible(routerPermOnly, '/informes-estrategicos', guest)).toBe(true);
  });
});

describe('pickAccessibleDestination', () => {
  const router = routerWith(SHELL_ROUTES);

  it('NO lleva a un huésped a un override de otra sesión que no puede abrir (el bug)', () => {
    const guest = guestState();
    const destination = pickAccessibleDestination(guest, router, '/search', '/management');
    expect(destination).toBe('/search');
  });

  it('respeta el override guardado cuando el usuario SÍ puede abrirlo', () => {
    const guest = guestState();
    expect(pickAccessibleDestination(guest, router, '/search', '/account/bookings')).toBe('/account/bookings');
  });

  it('valida también el homeHref del servidor cuando viene de un ?next= inaccesible', () => {
    const guest = guestState();
    // homeHref '/management' (next de una redirección previa) → cae a /search
    expect(pickAccessibleDestination(guest, router, '/management', null)).toBe('/search');
  });

  it('mantiene el homeHref del servidor cuando es accesible', () => {
    const guest = guestState();
    expect(pickAccessibleDestination(guest, router, '/account/bookings', null)).toBe('/account/bookings');
  });

  it('no rompe el override para un rol de gestión', () => {
    const gerente = guestState({
      user: { ...guestState().user!, primaryRole: 'gerente_hotel' },
    });
    expect(pickAccessibleDestination(gerente, router, '/management', '/management')).toBe('/management');
  });

  it('para super_admin el override gana siempre que sea accesible', () => {
    const admin = guestState({
      user: { ...guestState().user!, primaryRole: 'super_admin' },
      permissionCodes: ['*.*'],
    });
    expect(pickAccessibleDestination(admin, router, '/system/users', '/management')).toBe('/management');
  });

  it('usuario no autenticado: conserva el override o el fallback (paridad con el comportamiento previo)', () => {
    const anonymous = guestState({ authenticated: false, user: null });
    expect(pickAccessibleDestination(anonymous, router, '/search', '/management')).toBe('/management');
    expect(pickAccessibleDestination(anonymous, router, '/search', null)).toBe('/search');
  });

  it('defaults a /search cuando no hay homeHref ni override', () => {
    expect(pickAccessibleDestination(guestState(), router, null, null)).toBe('/search');
  });

  it('si ni el override ni el home son accesibles, cae a /search', () => {
    const guest = guestState();
    expect(pickAccessibleDestination(guest, router, '/system', '/management')).toBe('/search');
  });
});
