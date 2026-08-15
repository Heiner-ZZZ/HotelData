import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../../../../core/auth/auth.service';
import { type PermissionCode } from '../../../../core/auth/permission.constants';

interface NavItem {
  label: string;
  href: string;
  icon: string;
  permission: PermissionCode;
}

/**
 * Sub-navegación horizontal de Facturación — Dashboard, Dashboard Pagos,
 * Facturas y Pagos en un único diseño de píldoras (Stitch), filtrada por
 * permiso: si el usuario no tiene el permiso de un botón, el botón no se
 * renderiza. Si no hay ningún permiso, no se renderiza el contenedor.
 */
@Component({
  selector: 'app-billing-sub-nav',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './billing-sub-nav.html',
  styleUrl: './billing-sub-nav.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BillingSubNavComponent {
  private readonly auth = inject(AuthService);

  readonly navItems: NavItem[] = [
    { label: 'Dashboard', href: '/management/billing/dashboard', icon: 'monitoring', permission: 'reports.billing.invoices.read' as PermissionCode },
    { label: 'Dashboard Pagos', href: '/management/billing/payments-dashboard', icon: 'payments', permission: 'reports.billing.payments.read' as PermissionCode },
    { label: 'Facturas', href: '/management/billing/invoices', icon: 'receipt_long', permission: 'billing.read' as PermissionCode },
    { label: 'Pagos', href: '/management/billing/payments', icon: 'payments', permission: 'payments.read' as PermissionCode },
  ];

  /** Solo los botones cuyo permiso tiene el usuario. */
  readonly visibleItems = computed(() => this.navItems.filter((i) => this.auth.hasPermission(i.permission)));
}
