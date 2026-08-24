import type { Router } from '@angular/router';

import type { AuthState } from './auth.models';
import { SUPERUSER_WILDCARD } from './permission.constants';

/**
 * Predicados compartidos de autorización de rutas.
 *
 * `roleGuard` (auth.guard.ts) y la resolución del destino post-login
 * (AuthService.resolveDefaultDestination) usan las MISMAS reglas. Si un día
 * cambia la semántica del guard, ambos lados se mantienen consistentes y el
 * login nunca lleva a un usuario a una sección que el guard rechazaría
 * (antes eso disparaba el toast "No tienes permiso para acceder a esta
 * sección." justo al entrar, p.ej. un huésped con un override guardado de
 * una sesión de otro rol).
 */

export function hasAllowedRole(role: string | undefined, allowedRoles: string[] | undefined): boolean {
  if (!allowedRoles?.length) return true;
  return !!role && allowedRoles.includes(role);
}

export function hasRequiredPermission(permissionCodes: string[], requiredPermission: string | undefined): boolean {
  if (!requiredPermission) return true;
  // *.* super_admin wildcard grants access to everything
  if (permissionCodes.includes(SUPERUSER_WILDCARD)) return true;
  return permissionCodes.includes(requiredPermission);
}

/**
 * True cuando `url` apunta a una sección que el estado de sesión actual puede
 * abrir, con la MISMA decisión que tomaría `roleGuard` sobre el route
 * top-level del shell (la `data` de allowedRoles/requiredPermission vive en
 * esos routes). Rutas públicas sin entrada top-level propia (children del
 * public-shell, p.ej. `/search`), aliases de redirect y la wildcard → sin
 * gate → accesibles. Ignora query string / hash para no perder el match.
 */
export function isRouteAccessible(
  router: Pick<Router, 'config'>,
  url: string,
  state: AuthState,
): boolean {
  const pathOnly = url.split(/[?#]/, 1)[0] ?? '';
  const firstSegment = pathOnly.replace(/^\/+/, '').split('/')[0] ?? '';
  if (!firstSegment) return true;
  const route = router.config.find((r) => r.path === firstSegment);
  if (!route) return true;
  const allowedRoles = route.data?.['allowedRoles'] as string[] | undefined;
  const requiredPermission = route.data?.['requiredPermission'] as string | undefined;
  // Mismo orden y fallbacks que roleGuard: permiso → rol legacy → sin
  // restricciones (cuando la ruta no declara ni uno ni otro).
  if (requiredPermission && hasRequiredPermission(state.permissionCodes, requiredPermission)) return true;
  if (hasAllowedRole(state.user?.primaryRole, allowedRoles)) return true;
  return !requiredPermission && !(allowedRoles?.length ?? 0);
}

/**
 * Elige el destino post-login:
 * 1. Override guardado en localStorage (`hoteldata-default-dashboard`), si el
 *    usuario actual puede abrirlo.
 * 2. Home del servidor (`homeHref`, calculado por rol — puede venir de un
 *    `?next=` de una redirección previa, por eso también se valida).
 * 3. `/search` público como último recurso.
 *
 * Nunca devuelve una sección que `roleGuard` rechazaría, de modo que un
 * huésped ya no recibe el toast de "sin permisos" por el simple hecho de
 * iniciar sesión en un navegador con un override de otra sesión.
 */
export function pickAccessibleDestination(
  state: AuthState,
  router: Pick<Router, 'config'>,
  defaultHref: string | null,
  savedOverride: string | null,
): string {
  const fallback = defaultHref || '/search';
  if (!state.authenticated) return savedOverride || fallback;
  const candidates = savedOverride ? [savedOverride, fallback] : [fallback];
  for (const candidate of candidates) {
    if (isRouteAccessible(router, candidate, state)) return candidate;
  }
  return '/search';
}
