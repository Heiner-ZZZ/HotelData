import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { AccessNavComponent } from '../../../shared/ui/access-nav/access-nav';

interface ManagementSubItem {
  label: string;
  href: string;
  icon: string;
  exact?: boolean;
  allowedRoles?: string[];
}

interface ManagementNavGroup {
  label: string;
  icon: string;
  allowedRoles?: string[];
  items: ManagementSubItem[];
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
  readonly hoveredCategory = signal<string | null>(null);
  readonly clickOpened = signal<string | null>(null);

  readonly navigation: ManagementNavGroup[] = [
    {
      label: 'Dashboard',
      icon: 'dashboard',
      items: [{ label: 'Resumen', href: '/management', exact: true, icon: 'home' }]
    },
    {
      label: 'Operacion',
      icon: 'assignment',
      items: [
        { label: 'Reservas', href: '/management/reservations', icon: 'calendar_month' },
        { label: 'Disponibilidad', href: '/management/availability', icon: 'event_available', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'revenue_manager'] },
        { label: 'Check-ins', href: '/management/check-ins', icon: 'login', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'] },
        { label: 'Check-outs', href: '/management/check-outs', icon: 'logout', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'] }
      ]
    },
    {
      label: 'Propiedad',
      icon: 'domain',
      items: [
        { label: 'Propiedades', href: '/management/properties', icon: 'business' },
        { label: 'Habitaciones', href: '/management/rooms', icon: 'meeting_room', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'] },
        { label: 'Tarifas', href: '/management/rates', icon: 'attach_money', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'revenue_manager'] },
        { label: 'Politicas', href: '/management/policies', icon: 'policy', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'] },
        { label: 'Amenities', href: '/management/amenities', icon: 'spa', allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'marketing_hotelero'] }
      ]
    },
    {
      label: 'Reportes',
      icon: 'bar_chart',
      allowedRoles: ['super_admin', 'admin_sistema', 'revenue_manager', 'marketing_hotelero', 'auditor_datos', 'operador_datos'],
      items: [{ label: 'Reportes', href: '/management/reports', icon: 'bar_chart' }]
    },
    {
      label: 'Configuracion',
      icon: 'settings',
      allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'],
      items: [{ label: 'Ajustes', href: '/management/settings', icon: 'tune' }]
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

  toggleCategory(label: string) {
    this.clickOpened.update((current) => (current === label ? null : label));
  }

  onCategoryHover(label: string) {
    this.hoveredCategory.set(label);
  }

  onCategoryLeave(label: string) {
    this.hoveredCategory.set(null);
  }
}
