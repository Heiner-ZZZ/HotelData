import { Location } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  HostListener,
  inject,
  OnInit,
  signal
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { roleLabel } from '../../../core/auth/role-labels';
import { ThemeService } from '../../../core/theme/theme.service';
import { OperationModeIndicatorComponent } from '../operation-mode-indicator/operation-mode-indicator';
import { ReservationsApiService } from '../../../features/reservations/services/reservations-api.service';
import { NotificationsApiService } from '../../../features/system-admin/services/notifications-api.service';
import { ClientNotificationsService } from '../../../features/notifications/services/notifications.service';

interface TopNavItem {
  label: string;
  href: string;
  icon: string;
  allowedRoles?: string[];
}

interface TopNavNotification {
  id: number;
  /** Id Mongo real de la fila en notification_log (para marcar como leída). */
  rawId: string;
  /** notification_type (guest_promotional, guest_confirmed, …). */
  type: string;
  title: string;
  description: string;
  time: string;
  unread: boolean;
  bookingId: string;
  propId: number;
}

interface TopNavGroup {
  id: string;
  label: string;
  icon: string;
  allowedRoles?: string[];
  items: TopNavItem[];
}

@Component({
  selector: 'app-top-nav',
  imports: [RouterLink, RouterLinkActive, OperationModeIndicatorComponent],
  templateUrl: './top-nav.html',
  styleUrl: './top-nav.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TopNavComponent implements OnInit {
  /**
   * Cleanup registered via ``inject(DestroyRef).onDestroy`` in the constructor —
   * replaces the legacy ``ngOnDestroy`` lifecycle hook for Angular 22 modern style.
   * Order matches the equivalent ``ngOnDestroy`` invocation since both are
   * invoked during the same destruction phase.
   */
  private readonly authService = inject(AuthService);
  private readonly reservationsApi = inject(ReservationsApiService);
  private readonly notificationsApi = inject(NotificationsApiService);
  private readonly clientNotifications = inject(ClientNotificationsService);
  private readonly themeService = inject(ThemeService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);
  private readonly location = inject(Location);

  readonly theme = this.themeService;
  readonly authState = this.authService.authState;
  readonly currentUser = this.authService.currentUser;
  readonly roleLabel = roleLabel;
  readonly activeMenu = signal<string | null>(null);
  readonly showNotifications = signal(false);
  readonly notifications = signal<TopNavNotification[]>([]);
  /** La campana se muestra para todo usuario autenticado — huéspedes incluidos. */
  readonly showNotificationBell = computed(() => this.authState().authenticated && !!this.currentUser());
  /** Roles de sistema leen de la API de notificaciones del admin; el resto (huésped, staff) de /notifications/my. */
  readonly canViewNotifications = computed(() => {
    const role = this.currentUser()?.primaryRole;
    return role === 'super_admin' || role === 'admin_sistema';
  });
  readonly unreadCount = computed(() => this.notifications().filter(n => n.unread).length);
  private _notifPollSub: ReturnType<typeof setInterval> | null = null;
  /** Track if polling was permanently stopped due to an auth error. */
  private _notifPollingStopped = false;
  readonly navTransform = signal('translateY(0%)');
  readonly navOpacity = signal(1);
  private readonly SCROLL_HIDE_RANGE = 120;
  private hoverCloseTimer: ReturnType<typeof setTimeout> | null = null;

  readonly sessionMenuItems = computed(() => {
    const role = this.currentUser()?.primaryRole;
    const homeHref = this.authState().homeHref || '/search';
    if (!role) return [];
    const items: { label: string; href: string; icon: string }[] = [
      { label: 'Mi inicio', href: homeHref, icon: 'home' }
    ];
    if (['super_admin', 'admin_sistema', 'operador_datos', 'auditor_datos'].includes(role)) {
      items.push({ label: 'Sistema', href: '/system/users', icon: 'admin_panel_settings' });
    }
    if (['hotel_partner', 'gerente_hotel', 'revenue_manager', 'marketing_hotelero', 'operador_datos', 'auditor_datos', 'recepcionista', 'housekeeping', 'concierge'].includes(role)) {
      items.push({ label: 'Gestión', href: '/management/informes-estrategicos/h01', icon: 'dashboard' });
    }
    if (role === 'cliente') {
      items.push(
        { label: 'Mis reservas', href: '/account/bookings', icon: 'book_online' },
        { label: 'Mis facturas', href: '/account/billing', icon: 'receipt_long' },
        { label: 'Mis Favoritos', href: '/search/favorites', icon: 'favorite' },
        { label: 'Perfil', href: '/account/profile', icon: 'person' }
      );
    }
    if (role !== 'cliente') {
      items.push({ label: 'Vista pública', href: '/search', icon: 'public' });
    }
    return items;
  });

  readonly navGroups: TopNavGroup[] = [
    {
      id: 'explorar',
      label: 'Explorar',
      icon: 'explore',
      items: [
        { label: 'Buscar hoteles', href: '/search', icon: 'search' },
        { label: 'Reservas del viajero', href: '/account/bookings', icon: 'book_online', allowedRoles: ['cliente'] },
        { label: 'Mis Favoritos', href: '/search/favorites', icon: 'favorite' }
      ]
    }
  ];

  /** En la vista de huésped las opciones de Explorar se reparten como enlaces directos en el nav. */
  readonly guestNavItems: TopNavItem[] = [
    { label: 'Buscar hoteles', href: '/search', icon: 'search' },
    { label: 'Mis Favoritos', href: '/search/favorites', icon: 'favorite' },
    { label: 'Reservas del viajero', href: '/account/bookings', icon: 'book_online' },
    { label: 'Mis facturas', href: '/account/billing', icon: 'receipt_long' }
  ];

  readonly isGuest = computed(() => this.currentUser()?.primaryRole === 'cliente');

  readonly visibleGroups = computed(() => {
    const role = this.currentUser()?.primaryRole;
    return this.navGroups
      .map(g => ({
        ...g,
        items: g.items.filter(i => !i.allowedRoles?.length || (!!role && i.allowedRoles.includes(role)))
      }))
      .filter(g => g.items.length > 0);
  });

  ngOnInit() {
    this._startNotifPolling();
  }

  private _startNotifPolling() {
    this._fetchNotifications();
    this._notifPollSub = setInterval(() => this._fetchNotifications(), 30000);
  }

  private _stopNotifPolling() {
    if (this._notifPollSub) {
      clearInterval(this._notifPollSub);
      this._notifPollSub = null;
    }
  }

  private _fetchNotifications() {
    if (this._notifPollingStopped) {
      this._stopNotifPolling();
      return;
    }

    if (!this.authState().authenticated || !this.currentUser()) {
      this.notifications.set([]);
      return;
    }

    if (this.canViewNotifications()) {
      this.notificationsApi.getNotifications(1, undefined, undefined, undefined)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (viewModel) => {
            const currentUserEmail = this.currentUser()?.email?.toLowerCase() || '';
            const filteredItems = viewModel.items.filter(item =>
              item.recipientEmail?.toLowerCase() === currentUserEmail
            );
            const mapped = filteredItems.map((item, idx) => ({
              id: idx + 1,
              rawId: (item as { id?: string }).id ? String((item as { id?: string }).id) : '',
              type: item.notificationType || '',
              title: item.typeLabel,
              description: `${item.recipientName || 'Huésped'} · ${item.bookingId ? '#' + item.bookingId : ''} · ${item.statusLabel}`,
              time: this._timeAgo(item.createdAt),
              unread: item.status === 'sent',
              bookingId: item.bookingId || '',
              propId: item.propId || 0,
            }));
            this.notifications.set(mapped);
          },
          error: (err) => {
            if (err?.status === 403 || err?.status === 401) {
              this._notifPollingStopped = true;
              this._stopNotifPolling();
            }
          }
        });
      return;
    }

    // Huéspedes y staff no-admin: notificaciones propias vía /notifications/my.
    this.clientNotifications.getMyNotifications(1, 5)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          const mapped = result.items.map((item, idx) => ({
            id: idx + 1,
            rawId: item.id || '',
            type: item.notificationType || '',
            title: item.typeLabel,
            description: item.message || `${item.recipientName || 'Huésped'} · ${item.bookingId ? '#' + item.bookingId : ''} · ${item.statusLabel}`,
            time: this._timeAgo(item.createdAt),
            unread: item.isUnread,
            bookingId: item.bookingId || '',
            propId: item.propId || 0,
          }));
          this.notifications.set(mapped);
        },
        error: (err) => {
          if (err?.status === 403 || err?.status === 401) {
            this._notifPollingStopped = true;
            this._stopNotifPolling();
          }
        }
      });
  }

  private _timeAgo(iso: string): string {
    const now = Date.now();
    const past = new Date(iso).getTime();
    const diffMs = now - past;
    if (isNaN(diffMs) || diffMs < 0) return 'Ahora';
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'Ahora';
    if (diffMins < 60) return `Hace ${diffMins} min`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `Hace ${diffHours} h`;
    const diffDays = Math.floor(diffHours / 24);
    return `Hace ${diffDays} d`;
  }

  toggleNotifications() {
    this.showNotifications.update(v => !v);
  }

  closeNotifications() {
    this.showNotifications.set(false);
  }

  /** Deep link Fase 1: la promo lleva a la página pública del hotel;
   *  las transaccionales conservan el link a la reserva. */
  notifHref(n: TopNavNotification): string | null {
    if (n.type === 'guest_promotional' && n.propId > 0) return `/hotels/${n.propId}`;
    if (n.bookingId) return `/account/bookings/${n.bookingId}`;
    return null;
  }

  /** Clic en una notificación de la campanita: navega y, si es una promo
   *  sin leer, la marca como leída (el badge baja sin refetch). */
  onNotifClick(n: TopNavNotification): void {
    this.closeNotifications();
    if (n.type === 'guest_promotional' && n.propId > 0 && n.unread && n.rawId) {
      this.clientNotifications.markAsRead(n.rawId).subscribe({
        next: () => {
          this.notifications.update(prev =>
            prev.map(it => (it.rawId === n.rawId ? { ...it, unread: false } : it)),
          );
        },
        // Error silencioso: el dot persiste y se puede reintentar.
        error: () => undefined,
      });
    } else if (n.type !== 'guest_promotional' && n.unread && n.rawId) {
      this.clientNotifications.markAsRead(n.rawId).subscribe({
        next: () => {
          this.notifications.update(prev =>
            prev.map(it => (it.rawId === n.rawId ? { ...it, unread: false } : it)),
          );
        },
        error: () => undefined,
      });
    }
  }

  /** Icono Material Symbols para cada tipo de notificación. */
  notificationIcon(type: string): string {
    switch (type) {
      case 'guest_confirmed': return 'check_circle';
      case 'guest_cancelled': return 'cancel';
      case 'guest_no_show': return 'event_busy';
      case 'guest_checked_in': return 'hotel';
      case 'guest_checked_out': return 'logout';
      case 'guest_modified': return 'edit';
      case 'guest_promotional': return 'local_activity';
      case 'guest_payment': return 'payments';
      case 'guest_message': return 'chat';
      default: return 'notifications';
    }
  }

  constructor() {
    this.authService.ensureSessionLoaded()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe();
    this.destroyRef.onDestroy(() => this._stopNotifPolling());
  }

  onMenuEnter(id: string) {
    if (this.hoverCloseTimer) {
      clearTimeout(this.hoverCloseTimer);
      this.hoverCloseTimer = null;
    }
    this.activeMenu.set(id);
  }

  onMenuLeave(id: string) {
    if (this.hoverCloseTimer) clearTimeout(this.hoverCloseTimer);
    this.hoverCloseTimer = setTimeout(() => {
      if (this.activeMenu() === id) {
        this.activeMenu.set(null);
      }
    }, 200);
  }

  toggleMenu(id: string, event: MouseEvent) {
    event.stopPropagation();
    if (this.hoverCloseTimer) {
      clearTimeout(this.hoverCloseTimer);
      this.hoverCloseTimer = null;
    }
    this.activeMenu.update(v => v === id ? null : id);
  }

  closeMenus() {
    if (this.hoverCloseTimer) clearTimeout(this.hoverCloseTimer);
    this.activeMenu.set(null);
  }

  navigateBack() {
    if (window.history.length > 1) {
      this.location.back();
      return;
    }
    void this.router.navigateByUrl(this.authState().homeHref || '/search');
  }

  @HostListener('window:scroll')
  onWindowScroll() {
    const scrollY = window.scrollY;
    const progress = Math.min(scrollY / this.SCROLL_HIDE_RANGE, 1);
    this.navTransform.set(`translateY(${(progress * -120).toFixed(1)}%)`);
    this.navOpacity.set(1 - progress);
  }

  @HostListener('document:click')
  onDocClick() {
    this.closeMenus();
  }
}
