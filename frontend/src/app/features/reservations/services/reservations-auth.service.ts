import { computed, inject, Injectable } from '@angular/core';

import { AuthService, type AuthUser } from '../../../core/auth/auth.service';

/**
 * Centralized computed signals for reservations-feature role gating.
 *
 * Replaces ad-hoc `isStaff = computed(...)` definitions duplicated across
 * `reservations-list-page`, `reservation-new-page`, and
 * `reservation-detail-page`. Inject this service in any reservations
 * component that needs to gate UI elements by staff-vs-client role.
 *
 * Read computed signals by calling them as functions in templates:
 *   @if (reservationsAuth.isStaff()) { ... }
 *
 * Roles:
 *   - super_admin, admin_sistema, hotel_partner, gerente_hotel → ``isStaff``
 *   - cliente (or unauthenticated)                  → ``isClient``
 *
 * NOTE: These are role-based heuristics for UI visibility. Backend
 * authorization is permission-based (`require_permission("reservations.*")`
 * in routes); if a custom role is ever created that has ``reservations.*``
 * permissions but doesn't appear in the ``isStaff`` list, the user will
 * see fewer feature buttons in the frontend than they actually can use.
 * The long-term replacement is to call `auth.hasPermission()` instead of
 * role checks — once the role-permission mapping is fully centralized.
 */
@Injectable({ providedIn: 'root' })
export class ReservationsAuthService {
  private readonly auth = inject(AuthService);

  /**
   * Backoffice / hotel-staff user: any role except ``cliente``.
   *
   * Safe-casts the ``currentUser()`` computed-signal value through the
   * ``AuthUser`` interface exported by ``AuthService``. The runtime shape
   * is already that interface (see ``AuthService.mapAuthState``), but the
   * cast pins the wire-shape contract forward — if ``AuthService`` ever
   * returns a different shape, this service is forced to revisit the
   * staff-detection list explicitly rather than silently misclassifying.
   */
  readonly isStaff = computed<boolean>(() => {
    const user = this.auth.currentUser() as AuthUser | null;
    const role = user?.primaryRole;
    if (!role) return false;
    return ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'].includes(role);
  });

  /** Self-service client user (or unauthenticated visitor). */
  readonly isClient = computed<boolean>(() => {
    const user = this.auth.currentUser() as AuthUser | null;
    const role = user?.primaryRole;
    return !role || role === 'cliente';
  });
}
