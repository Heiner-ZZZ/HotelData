import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { ThemeService } from '../../../core/theme/theme.service';

interface SidebarItem {
  label: string;
  href: string;
  icon: string;
  allowedRoles?: string[];
}

interface SidebarSection {
  id: string;
  label: string;
  icon: string;
  allowedRoles?: string[];
  items: SidebarItem[];
}

@Component({
  selector: 'app-sidebar-nav',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './sidebar-nav.html',
  styleUrl: './sidebar-nav.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class SidebarNavComponent {
  private readonly authService = inject(AuthService);
  private readonly themeService = inject(ThemeService);
  private readonly destroyRef = inject(DestroyRef);

  readonly theme = this.themeService;
  readonly currentUser = this.authService.currentUser;
  readonly sidebarCollapsed = signal(false);
  readonly openSection = signal<string | null>(null);

  readonly sections: SidebarSection[] = [
    {
      id: 'gestion',
      label: 'Gestión',
      icon: 'dashboard',
      allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'revenue_manager', 'marketing_hotelero', 'operador_datos', 'auditor_datos'],
      items: [
        { label: 'Panel hotelero', href: '/management', icon: 'dashboard' },
        {
          label: 'Recepción',
          href: '/management/recepcion',
          icon: 'calendar_month',
          allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'revenue_manager']
        },
        {
          label: 'Disponibilidad',
          href: '/management/availability',
          icon: 'event_available',
          allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'revenue_manager']
        },
        {
          label: 'Check-ins',
          href: '/management/check-ins',
          icon: 'login',
          allowedRoles: ['super_admin', 'admin_sistema', 'gerente_hotel']
        },
        {
          label: 'Estancias Activas',
          href: '/management/stay-inbox',
          icon: 'meeting_room',
          allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel']
        },
        {
          label: 'Check-outs',
          href: '/management/check-outs',
          icon: 'logout',
          allowedRoles: ['super_admin', 'admin_sistema', 'gerente_hotel']
        },
        {
          label: 'Propiedades',
          href: '/management/properties',
          icon: 'business',
          allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'revenue_manager', 'marketing_hotelero']
        },
        {
          label: 'Habitaciones',
          href: '/management/rooms',
          icon: 'meeting_room',
          allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel']
        },
        {
          label: 'Tarifas',
          href: '/management/rates',
          icon: 'attach_money',
          allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'revenue_manager']
        },
        {
          label: 'Políticas',
          href: '/management/policies',
          icon: 'policy',
          allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'marketing_hotelero']
        },
        {
          label: 'Amenities',
          href: '/management/amenities',
          icon: 'spa',
          allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'marketing_hotelero']
        },
        {
          label: 'Reseñas',
          href: '/management/reviews',
          icon: 'reviews',
          allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'marketing_hotelero', 'auditor_datos']
        },
        {
          label: 'Housekeeping',
          href: '/management/housekeeping',
          icon: 'cleaning_services',
          allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel']
        },
        {
          label: 'Facturación',
          href: '/management/billing/invoices',
          icon: 'receipt_long',
          allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'auditor_datos']
        },
        {
          label: 'Finanzas',
          href: '/management/expenses',
          icon: 'account_balance',
          allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'auditor_datos']
        },
        {
          label: 'Reportes',
          href: '/management/reports',
          icon: 'bar_chart',
          allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel', 'revenue_manager', 'marketing_hotelero', 'auditor_datos', 'operador_datos']
        },
        {
          label: 'Auditoría',
          href: '/management/audit-log',
          icon: 'history_toggle_off',
          allowedRoles: ['super_admin', 'admin_sistema', 'auditor_datos', 'operador_datos']
        },
      ]
    },
    {
      id: 'rrhh',
      label: 'RRHH',
      icon: 'group',
      allowedRoles: ['super_admin', 'admin_sistema', 'hotel_partner', 'gerente_hotel'],
      items: [
        { label: 'Empleados', href: '/management/hr/directory', icon: 'badge' },
        { label: 'Alta', href: '/management/hr/onboarding', icon: 'person_add' },
      ]
    },
    {
      id: 'propietario',
      label: 'Propietario',
      icon: 'assignment_ind',
      allowedRoles: ['super_admin'],
      items: [
        { label: 'Asignación de hoteles', href: '/ownership/users', icon: 'domain_verification' }
      ]
    },
    {
      id: 'sistema',
      label: 'Sistema',
      icon: 'admin_panel_settings',
      allowedRoles: ['super_admin', 'admin_sistema', 'operador_datos', 'auditor_datos'],
      items: [
        { label: 'Usuarios', href: '/system/users', icon: 'people', allowedRoles: ['super_admin', 'admin_sistema'] },
        { label: 'Permisos', href: '/system/permissions', icon: 'verified_user', allowedRoles: ['super_admin', 'admin_sistema'] },
        { label: 'Monitoreo', href: '/system/monitoring', icon: 'monitoring' },
        { label: 'Auditoría', href: '/system/audit', icon: 'history' },
        { label: 'Notificaciones', href: '/system/notifications', icon: 'notifications' },
        { label: 'BSC', href: '/system/bsc', icon: 'monitor_heart', allowedRoles: ['super_admin', 'admin_sistema', 'operador_datos', 'auditor_datos'] },
        { label: 'Geográfico', href: '/admin/geo-catalog', icon: 'map', allowedRoles: ['super_admin', 'admin_sistema'] }
      ]
    }
  ];

  readonly visibleSections = computed(() => {
    const role = this.currentUser()?.primaryRole;
    return this.sections
      .map(s => ({
        ...s,
        items: s.items.filter(i => !i.allowedRoles?.length || (!!role && i.allowedRoles.includes(role)))
      }))
      .filter(s => s.items.length > 0);
  });

  constructor() {
    this.authService.ensureSessionLoaded()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe();
  }

  toggleSection(id: string) {
    this.openSection.update(v => v === id ? null : id);
  }

  trackByHref(_index: number, item: SidebarItem): string {
    return item.href;
  }
}
