import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { AccessNavComponent } from '../../../shared/ui/access-nav/access-nav';

interface ManagementNavGroup {
  label: string;
  allowedRoles?: string[];
  items: Array<{ label: string; href: string; exact?: boolean; allowedRoles?: string[] }>;
}

@Component({
  selector: 'app-management-shell',
  imports: [AccessNavComponent, RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './management-shell.html',
  styleUrl: './management-shell.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ManagementShellComponent {
  private readonly authService = inject(AuthService);

  readonly currentUser = this.authService.currentUser;

  readonly navigation: ManagementNavGroup[] = [
    {
      label: 'Dashboard',
      items: [{ label: 'Resumen', href: '/management', exact: true }]
    },
    {
      label: 'Operacion',
      items: [
        { label: 'Reservas', href: '/management/reservations' },
        { label: 'Disponibilidad', href: '/management/availability', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'revenue_manager'] },
        { label: 'Check-ins', href: '/management/check-ins', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'] },
        { label: 'Check-outs', href: '/management/check-outs', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'] }
      ]
    },
    {
      label: 'Propiedad',
      items: [
        { label: 'Propiedades', href: '/management/properties' },
        { label: 'Habitaciones', href: '/management/rooms', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'] },
        { label: 'Tarifas', href: '/management/rates', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'revenue_manager'] },
        { label: 'Politicas', href: '/management/policies', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'] },
        { label: 'Amenities', href: '/management/amenities', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'marketing_hotelero'] }
      ]
    },
    {
      label: 'Reportes',
      allowedRoles: ['super_admin', 'admin_sistema', 'revenue_manager', 'marketing_hotelero', 'auditor_datos', 'operador_datos'],
      items: [{ label: 'Reportes', href: '/management/reports' }]
    },
    {
      label: 'Configuracion',
      allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'],
      items: [{ label: 'Ajustes', href: '/management/settings' }]
    }
  ];

  readonly visibleNavigation = computed(() => {
    const role = this.currentUser()?.primaryRole;

    return this.navigation
      .filter((group) => !group.allowedRoles?.length || (!!role && group.allowedRoles.includes(role)))
      .map((group) => ({
        ...group,
        items: group.items.filter((item) => !item.allowedRoles?.length || (!!role && item.allowedRoles.includes(role)))
      }))
      .filter((group) => group.items.length > 0);
  });
}
