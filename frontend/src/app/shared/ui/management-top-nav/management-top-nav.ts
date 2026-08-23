import { ChangeDetectionStrategy, Component, computed, DestroyRef, HostListener, inject, signal, OnInit, ElementRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink } from '@angular/router';
import { filter } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { API_CONFIG } from '../../../core/api/api.config';
import { roleLabel } from '../../../core/auth/role-labels';
import { ThemeService } from '../../../core/theme/theme.service';
import { NotificationsApiService } from '../../../features/system-admin/services/notifications-api.service';
import { LogoutConfirmModalComponent } from '../logout-confirm-modal/logout-confirm-modal';
import { OperationModeIndicatorComponent } from '../operation-mode-indicator/operation-mode-indicator';
import { LogoutGuardService, type LogoutGuardResponse } from '../../services/logout-guard.service';
import { PropertyContextService } from '../../services/property-context.service';
import { TurnoChipComponent } from '../turno-chip/turno-chip';

interface BreadcrumbItem {
  label: string;
  path: string;
  queryParams?: Record<string, string>;
}

const SEGMENT_LABELS: Record<string, string> = {
  // ── Raíces ──
  management: 'Gestión',
  system: 'Sistema',
  ownership: 'Propietario',
  admin: 'Administración',
  account: 'Mi Cuenta',
  // ── Gestión ──
  recepcion: 'Recepción',
  reservations: 'Reservas',
  'manual-reservations': 'Reservas Manuales',
  availability: 'Disponibilidad',
  rooms: 'Habitaciones',
  guests: 'Huéspedes',
  rates: 'Tarifas',
  policies: 'Políticas',
  amenities: 'Amenities',
  products: 'Productos',
  'check-ins': 'Check-ins',
  'check-outs': 'Check-outs',
  reviews: 'Reseñas',
  billing: 'Facturación',
  housekeeping: 'Housekeeping',
  hr: 'RRHH',
  expenses: 'Finanzas',
  revenue: 'Ingresos',
  reports: 'Reportes',
  'audit-log': 'Auditoría Oper.',
  'lost-and-found': 'Lost & Found',
  'stay-inbox': 'Estancias Activas',
  'service-requests': 'Solicitudes',
  shifts: 'Cajas y Turnos',
  'open-shifts': 'Turnos Abiertos',
  'team-permissions': 'Equipo y Permisos',
  profile: 'Perfil',
  // ── Sub-rutas ──
  dashboard: 'Dashboard',
  new: 'Nuevo',
  confirmed: 'Confirmada',
  invoices: 'Facturas',
  payments: 'Pagos',
  folios: 'Folios',
  maintenance: 'Mantenimiento',
  charges: 'Cargos',
  calendar: 'Calendario',
  directory: 'Directorio',
  onboarding: 'Onboarding',
  'my-portal': 'Mi Portal',
  portal: 'Portal',
  attendance: 'Asistencia',
  // ── Sistema ──
  users: 'Usuarios',
  permissions: 'Permisos',
  monitoring: 'Monitoreo',
  audit: 'Auditoría',
  notifications: 'Notificaciones',
  currencies: 'Monedas',
  // ── Admin / cuenta ──
  'global-settings': 'Configuración',
  earnings: 'Ganancias',
  'geo-catalog': 'Geo-Catálogo',
  bookings: 'Mis Reservas',
  edit: 'Editar',
};

/** Segmento de ruta que es un ID dinámico (reserva, factura, folio, empleado…). */
const DYNAMIC_ID_PATTERN = /^(BK-[\w-]+|[0-9a-f]{24}|\d+)$/i;

function segmentLabel(segment: string): string | null {
  const normalized = segment.trim();
  if (!normalized) return null;
  const known = SEGMENT_LABELS[normalized];
  if (known) return known;
  if (DYNAMIC_ID_PATTERN.test(normalized)) return 'Detalle';
  return normalized
    .replace(/[-_]+/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

@Component({
  selector: 'app-management-top-nav',
  imports: [RouterLink, OperationModeIndicatorComponent, TurnoChipComponent, LogoutConfirmModalComponent],
  templateUrl: './management-top-nav.html',
  styleUrl: './management-top-nav.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ManagementTopNavComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly notificationsApi = inject(NotificationsApiService);
  private readonly themeService = inject(ThemeService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly elementRef = inject(ElementRef);
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);
  readonly logoutGuard = inject(LogoutGuardService);

  readonly theme = this.themeService;
  readonly currentUser = this.authService.currentUser;
  readonly showNotifications = signal(false);
  readonly showProfileMenu = signal(false);
  readonly currentUrl = signal(this.router.url.split('?')[0]);
  readonly currentQueryParams = signal<Record<string, string>>({});

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

  readonly roleLabel = computed(() => roleLabel(this.currentUser()?.primaryRole));

  readonly singleHotelMode = computed(() => this.propertyCtx.singleHotelMode());
  readonly hotelLabel = computed(() => this.propertyCtx.currentPropLabel());

  readonly breadcrumbs = computed<BreadcrumbItem[]>(() => {
    const url = this.currentUrl();
    const qp = this.currentQueryParams();
    const propQp = qp['prop_id'] ? { prop_id: qp['prop_id'] } : undefined;
    const segments = url.split('/').filter(Boolean);
    const rootIdx = segments.findIndex(s => s === 'management' || s === 'system' || s === 'ownership');
    if (rootIdx === -1) return [{ label: 'Gestión', path: '/management', queryParams: propQp }];
    const crumbs = segments.slice(rootIdx).map((seg, i) => {
      const label = segmentLabel(seg) || 'Gestión';
      return { label, path: '/' + segments.slice(rootIdx, rootIdx + i + 1).join('/'), queryParams: propQp };
    });
    // En modo single, el hotel se muestra como badge aparte, no en el breadcrumb
    if (!this.propertyCtx.singleHotelMode()) {
      const propLabel = this.propertyCtx.currentPropLabel();
      if (propLabel) {
        crumbs.push({ label: propLabel, path: '', queryParams: undefined });
      }
    }
    return crumbs;
  });

  readonly pollingError = signal(false);
  /** Whether the user can see the notifications panel (staff roles).
   *
   * Todos los roles staff (super_admin, admin_sistema, gerente_hotel,
   * recepcionista, housekeeping, …) ven la campanita — el centro de
   * notificaciones del equipo — con sus broadcasts operativas
   * (``housekeeping_check_in``, ``no_show_reopen``, ``late_checkout_*``,
   * ``early_checkin_*``). Los clientes usan el portal de huésped, no esta
   * bandeja.
   */
  readonly canViewNotifications = computed(() => {
    const role = this.currentUser()?.primaryRole;
    return !!role && role !== 'cliente';
  });

  readonly notifications = signal<{ id: number; rawId: string; icon: string; title: string; description: string; time: string; unread: boolean; bookingId: string; propId: number }[]>([]);

  /** Icono por tipo de notificación (Material Symbols). */
  notificationIcon(type: string): string {
    if (type.includes('confirmed')) return 'check_circle';
    if (type.includes('rejected') || type.includes('cancelled')) return 'cancel';
    if (type.includes('checked_in')) return 'login';
    if (type.includes('checked_out')) return 'logout';
    if (type.includes('invoice')) return 'receipt_long';
    if (type.includes('late_arrival')) return 'nights_stay';
    if (type.includes('no_show')) return 'undo';
    if (type.includes('late_checkout')) return 'schedule';
    if (type.includes('early_checkin')) return 'alarm';
    if (type.includes('housekeeping_check_in')) return 'cleaning_services';
    if (type.includes('amenity')) return 'spa';
    if (type.includes('review')) return 'star';
    if (type.includes('permissions')) return 'manage_accounts';
    if (type.includes('shift')) return 'point_of_sale';
    return 'notifications';
  }

  readonly unreadCount = computed(() => this.notifications().filter(n => n.unread).length);

  private _pollingSub: ReturnType<typeof setInterval> | null = null;
  /** Track if polling was permanently stopped due to an auth error. */
  private _pollingStopped = false;

  constructor() {
    this.destroyRef.onDestroy(() => this._stopPolling());
    this.router.events
      .pipe(
        filter((e): e is NavigationEnd => e instanceof NavigationEnd),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe(e => {
        const [urlPath, qs] = e.urlAfterRedirects.split('?');
        this.currentUrl.set(urlPath);
        const params: Record<string, string> = {};
        if (qs) {
          qs.split('&').forEach(pair => {
            const [k, v] = pair.split('=');
            if (k) params[decodeURIComponent(k)] = v ? decodeURIComponent(v) : '';
          });
        }
        this.currentQueryParams.set(params);
      });
  }

  ngOnInit() {
    this._startPolling();
  }

  private _startPolling() {
    this._fetchNotifications();
    this._pollingSub = setInterval(() => this._fetchNotifications(), 30000);
  }

  private _stopPolling() {
    if (this._pollingSub) {
      clearInterval(this._pollingSub);
      this._pollingSub = null;
    }
  }

  private _fetchNotifications() {
    if (this._pollingStopped || !this.canViewNotifications()) {
      // No access: show empty state silently, stop polling
      this.pollingError.set(false);
      this.notifications.set([]);
      this._stopPolling();
      return;
    }

    this.notificationsApi.getNotifications(1, undefined, undefined, undefined)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (viewModel) => {
          this.pollingError.set(false);
          const currentUserEmail = this.currentUser()?.email?.toLowerCase() || '';
          // Personales (dirigidas al email del usuario) + broadcast de equipo
          // (``recipient_email`` vacío: housekeeping, late/early check-out) —
          // los roles admin ven las operativas para supervisar la operación.
          const filteredItems = viewModel.items.filter(item =>
            !item.recipientEmail || item.recipientEmail.toLowerCase() === currentUserEmail
          );
          const mapped = filteredItems.map((item, idx) => ({
            id: idx + 1,
            rawId: item.id || '',
            icon: this.notificationIcon(item.notificationType),
            title: item.typeLabel,
            description: item.message || `${item.recipientName || 'Administrador'} · ${item.bookingId ? '#' + item.bookingId : ''} · ${item.statusLabel}`,
            time: this._timeAgo(item.createdAt),
            unread: item.status === 'sent',
            bookingId: item.bookingId || '',
            propId: item.propId || 0,
          }));
          this.notifications.set(mapped);
        },
        error: (err) => {
          // 403 = no access → stop polling permanently to avoid console noise
          if (err?.status === 403) {
            this._pollingStopped = true;
            this.notifications.set([]);
            this.pollingError.set(false);
            this._stopPolling();
            return;
          }
          // 401 = session expired → stop polling to prevent redirect flood
          if (err?.status === 401) {
            this._pollingStopped = true;
            this.notifications.set([]);
            this.pollingError.set(false);
            this._stopPolling();
            return;
          }
          this.pollingError.set(true);
        }
      });
  }

  private _timeAgo(iso: string): string {
    const now = Date.now();
    const then = new Date(iso).getTime();
    const diffMs = now - then;
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1) return 'Ahora';
    if (mins < 60) return `Hace ${mins} min`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `Hace ${hrs} hora${hrs > 1 ? 's' : ''}`;
    const days = Math.floor(hrs / 24);
    return `Hace ${days} día${days > 1 ? 's' : ''}`;
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (this.showNotifications()) {
      const wrapper = this.elementRef.nativeElement.querySelector('.notif-wrapper');
      if (wrapper && !wrapper.contains(target)) {
        this.showNotifications.set(false);
      }
    }
    if (this.showProfileMenu()) {
      const wrapper = this.elementRef.nativeElement.querySelector('.profile-wrapper');
      if (wrapper && !wrapper.contains(target)) {
        this.showProfileMenu.set(false);
      }
    }
  }

  toggleNotifications() {
    this.showNotifications.update(v => !v);
  }

  toggleProfileMenu() {
    this.showProfileMenu.update(v => !v);
  }

  closeProfileMenu() {
    this.showProfileMenu.set(false);
  }

  markAllRead() {
    const ids = this.notifications().filter(n => n.unread && n.rawId).map(n => n.rawId);
    if (!ids.length) return;
    this.http.post(`${this.apiConfig.baseUrl}/admin/notifications/mark-read`, { ids }, { withCredentials: true })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => this.notifications.update(list => list.map(n => ({ ...n, unread: false }))),
        error: () => undefined,
      });
  }

  closeNotifications() {
    this.showNotifications.set(false);
  }

  // ── Logout guard: warn (with links) when the user still has open
  //    cash/attendance shifts before killing the session. ──
  readonly logoutGuardData = signal<LogoutGuardResponse | null>(null);
  readonly showLogoutGuardModal = signal(false);

  onLogoutClick(): void {
    if (this.logoutGuard.checking()) return;
    this.showProfileMenu.set(false);
    this.logoutGuard.check().subscribe({
      next: (res) => {
        if (res.has_open_shifts) {
          this.logoutGuardData.set(res);
          this.showLogoutGuardModal.set(true);
        } else {
          this.proceedLogout();
        }
      },
    });
  }

  proceedLogout(): void {
    this.showLogoutGuardModal.set(false);
    this.logoutGuardData.set(null);
    // Server-side session invalidation + redirect to /login.
    window.location.href = '/auth/logout';
  }

  cancelLogoutGuard(): void {
    this.showLogoutGuardModal.set(false);
    this.logoutGuardData.set(null);
  }
}
