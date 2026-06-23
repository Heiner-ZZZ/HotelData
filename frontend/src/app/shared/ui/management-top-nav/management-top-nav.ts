import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink } from '@angular/router';
import { filter } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';

interface BreadcrumbItem {
  label: string;
  path: string;
}

const SEGMENT_LABELS: Record<string, string> = {
  management: 'Gestión',
  system: 'Sistema',
  ownership: 'Propietario',
  properties: 'Propiedades',
  rooms: 'Habitaciones',
  recepcion: 'Recepción',
  reservations: 'Reservas',
  availability: 'Disponibilidad',
  'check-ins': 'Check-ins',
  'check-outs': 'Check-outs',
  rates: 'Tarifas',
  policies: 'Políticas',
  amenities: 'Amenidades',
  reports: 'Reportes',
  settings: 'Configuración',
  users: 'Usuarios',
  permissions: 'Permisos',
  monitoring: 'Monitoreo',
  audit: 'Auditoría',
  edit: 'Editar Contenido',
};

@Component({
  selector: 'app-management-top-nav',
  imports: [RouterLink],
  templateUrl: './management-top-nav.html',
  styleUrl: './management-top-nav.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ManagementTopNavComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly currentUser = this.authService.currentUser;
  readonly showNotifications = signal(false);
  readonly currentUrl = signal(this.router.url.split('?')[0]);

  readonly initials = computed(() => {
    const name = this.currentUser()?.displayName || this.currentUser()?.username || 'U';
    const parts = name.split(' ').filter(Boolean);
    return parts.length >= 2
      ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      : parts[0]?.slice(0, 2).toUpperCase() || 'U';
  });

  readonly surname = computed(() => {
    const name = this.displayName();
    const parts = name.split(' ').filter(Boolean);
    return parts.length >= 2 ? parts.slice(1).join(' ') : '';
  });

  readonly firstName = computed(() => {
    return this.displayName().split(' ').filter(Boolean)[0] || this.displayName();
  });

  readonly displayName = computed(() => this.currentUser()?.displayName || this.currentUser()?.username || 'Usuario');

  readonly roleLabel = computed(() => {
    const role = this.currentUser()?.primaryRole || '';
    const labels: Record<string, string> = {
      super_admin: 'Super Administrador',
      admin_sistema: 'Administrador',
      hotel_partner: 'Partner Hotelero',
      gerente_hotel: 'Gerente de Hotel',
      revenue_manager: 'Revenue Manager',
      marketing_hotelero: 'Marketing Hotelero',
      operador_datos: 'Operador de Datos',
      auditor_datos: 'Auditor de Datos',
      cliente: 'Cliente',
    };
    return labels[role] || role.replace(/_/g, ' ');
  });

  readonly breadcrumbs = computed<BreadcrumbItem[]>(() => {
    const url = this.currentUrl();
    const segments = url.split('/').filter(Boolean);
    const rootIdx = segments.findIndex(s => s === 'management' || s === 'system' || s === 'ownership');
    if (rootIdx === -1) return [{ label: 'Gestión', path: '/management' }];
    return segments.slice(rootIdx).map((seg, i) => {
      const label = SEGMENT_LABELS[seg] || seg.charAt(0).toUpperCase() + seg.slice(1).replace(/-/g, ' ');
      return { label, path: '/' + segments.slice(rootIdx, rootIdx + i + 1).join('/') };
    });
  });

  constructor() {
    this.router.events
      .pipe(
        filter((e): e is NavigationEnd => e instanceof NavigationEnd),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe(e => this.currentUrl.set(e.urlAfterRedirects.split('?')[0]));
  }

  readonly notifications = signal<Array<{ id: number; title: string; description: string; time: string; unread: boolean }>>([
    { id: 1, title: 'Nueva reserva', description: 'Reserva #1234 confirmada para Grand Plaza', time: 'Hace 5 min', unread: true },
    { id: 2, title: 'Actualización ETL', description: 'Pipeline de datos completado exitosamente', time: 'Hace 1 hora', unread: true },
    { id: 3, title: 'Alerta de ocupación', description: 'Hotel Marriott al 95% de capacidad', time: 'Hace 3 horas', unread: false },
    { id: 4, title: 'Mantenimiento', description: 'Actualización del sistema programada', time: 'Hace 1 día', unread: false },
  ]);

  readonly unreadCount = computed(() => this.notifications().filter(n => n.unread).length);

  toggleNotifications() {
    this.showNotifications.update(v => !v);
  }

  markAllRead() {
    this.notifications.update(list => list.map(n => ({ ...n, unread: false })));
  }

  closeNotifications() {
    this.showNotifications.set(false);
  }
}
