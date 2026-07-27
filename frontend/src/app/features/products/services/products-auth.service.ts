import { computed, inject, Injectable } from '@angular/core';

import { AuthService } from '../../../core/auth/auth.service';

/**
 * Centralized computed signals for products-feature permission gating.
 *
 * Replaces ad-hoc `canSeeCost = computed(...)` definitions duplicated across
 * `products-list-page` and the three report partials (margin / cogs /
 * stock-value). Inject this service in any component that needs to gate
 * UI elements by product-cost visibility or management rights — the
 * computed signals stay consistent with the backend route gate
 * (`require_permission("inventory.products.cost.*")`).
 *
 * Read computed signals by calling them as functions in templates:
 *   @if (productsAuth.canSeeCost()) { ... }
 *
 * Roles:
 *   - super_admin        → see + manage cost
 *   - gerente_hotel      → see + manage cost
 *   - hotel_partner      → see only
 *   - recepcionista, etc → no access (cost fields disappear from JSON)
 */
@Injectable({ providedIn: 'root' })
export class ProductsAuthService {
  private readonly auth = inject(AuthService);

  /** Roles allowed to *see* cost_price, margin%, and inventory value. */
  readonly canSeeCost = computed<boolean>(() => {
    const role = this.auth.currentUser()?.primaryRole;
    if (!role) return false;
    return ['super_admin', 'gerente_hotel', 'hotel_partner'].includes(role);
  });

  /** Roles allowed to *write* cost_price (restock, edit product). */
  readonly canManageCost = computed<boolean>(() => {
    const role = this.auth.currentUser()?.primaryRole;
    if (!role) return false;
    return ['super_admin', 'gerente_hotel'].includes(role);
  });

  /** Aliases used by the catalog page; semantically identical to
   *  canManageCost today but kept separate for future divergence
   *  (e.g. read-only auditors). */
  readonly canEdit = this.canManageCost;
  readonly canRestock = this.canManageCost;
  readonly canCreate = this.canManageCost;
}
