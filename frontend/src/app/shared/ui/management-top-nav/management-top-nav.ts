import { ChangeDetectionStrategy, Component, computed, DestroyRef, HostListener, inject, signal, OnInit, ElementRef } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink } from '@angular/router';
import { filter } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { roleLabel } from '../../../core/auth/role-labels';
import { NotificationsApiService } from '../../../features/system-admin/services/notifications-api.service';
import { PropertyContextService } from '../../services/property-context.service';

interface BreadcrumbItem {
  label: string;
  path: string;
  queryParams?: Record<string, string>;
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
export class ManagementTopNavComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly notificationsApi = inject(NotificationsApiService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly elementRef = inject(ElementRef);
  private readonly propertyCtx = inject(PropertyContextService);

  readonly currentUser = this.authService.currentUser;
  readonly showNotifications = signal(false);
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
      const label = SEGMENT_LABELS[seg] || seg.charAt(0).toUpperCase() + seg.slice(1).replace(/-/g, ' ');
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
  /** Whether the user has admin-level access to the notifications API. */
  readonly canViewNotifications = computed(() => {
    const role = this.currentUser()?.primaryRole;
    return role === 'super_admin' || role === 'admin_sistema';
  });

  readonly notifications = signal<{ id: number; title: string; description: string; time: string; unread: boolean; bookingId: string; propId: number }[]>([]);

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
          const filteredItems = viewModel.items.filter(item =>
            item.recipientEmail?.toLowerCase() === currentUserEmail
          );
          const mapped = filteredItems.map((item, idx) => ({
            id: idx + 1,
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
    if (this.showNotifications()) {
      const target = event.target as HTMLElement;
      const wrapper = this.elementRef.nativeElement.querySelector('.notif-wrapper');
      if (wrapper && !wrapper.contains(target)) {
        this.showNotifications.set(false);
      }
    }
  }

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
