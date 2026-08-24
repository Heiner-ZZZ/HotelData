import { provideHttpClient } from '@angular/common/http';
import { Component, computed, signal } from '@angular/core';
import { provideRouter, Router } from '@angular/router';
import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { ThemeService } from '../../../core/theme/theme.service';
import { ReservationsApiService } from '../../../features/reservations/services/reservations-api.service';
import { NotificationsApiService } from '../../../features/system-admin/services/notifications-api.service';
import { ClientNotificationsService } from '../../../features/notifications/services/notifications.service';
import { TopNavComponent } from './top-nav';

function makeAuth(role: string | null, avatarUrl: string | null = null) {
  const user = signal(
    role
      ? {
          id: 'u1',
          username: 'demo',
          displayName: 'Demo',
          email: 'demo@hoteldata.local',
          primaryRole: role,
          roleIds: [],
          avatarUrl,
          permissions: [],
        }
      : null,
  );
  return {
    authState: computed(() => ({
      authenticated: !!user(),
      user: user(),
      session: null,
      homeHref: '/search',
      permissionCodes: [] as string[],
    })),
    currentUser: computed(() => user()),
    ensureSessionLoaded: () => of(null),
  } as unknown as AuthService;
}

const themeMock = { isDark: signal(false), toggle: jest.fn() };

function makeClientNotif(overrides: Record<string, unknown> = {}) {
  return {
    id: 'n1',
    notificationType: 'guest_promotional',
    typeLabel: 'Promoción',
    recipientEmail: 'h@example.com',
    recipientName: 'H',
    bookingId: '',
    propId: 3,
    status: 'sent',
    statusLabel: 'Enviado',
    statusTone: 'success',
    isUnread: true,
    errorMessage: '',
    message: '20% de descuento en tu próxima estadía.',
    title: 'Oferta de verano',
    createdAt: '2026-08-13T10:00:00Z',
    ...overrides,
  };
}

describe('TopNavComponent', () => {
  async function render(
    role: string | null,
    avatarUrl: string | null = null,
    clientItems: unknown[] = [],
    markRead: jest.Mock = jest.fn(() => of({ id: 'x', read: true })),
  ) {
    const systemApi = { getNotifications: jest.fn().mockReturnValue(of({ items: [] })) };
    const clientService = {
      getMyNotifications: jest.fn().mockReturnValue(
        of({
          items: clientItems,
          unreadCount: clientItems.filter((i) => (i as { isUnread?: boolean }).isUnread).length,
        }),
      ),
      markAsRead: markRead,
    };

    await TestBed.configureTestingModule({
      imports: [TopNavComponent],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        { provide: AuthService, useValue: makeAuth(role, avatarUrl) },
        { provide: ThemeService, useValue: themeMock },
        { provide: ReservationsApiService, useValue: {} },
        { provide: NotificationsApiService, useValue: systemApi },
        { provide: ClientNotificationsService, useValue: clientService },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(TopNavComponent);
    fixture.detectChanges();
    return { fixture, systemApi, clientService };
  }

  it('deep link: una promo de la campanita navega a /hotels/{prop_id} y la marca como leída', async () => {
    const markRead = jest.fn(() => of({ id: 'n1', read: true }));
    const { fixture, clientService } = await render('cliente', null, [makeClientNotif()], markRead);
    const component = fixture.componentInstance;
    const promo = component.notifications()[0];

    // Deep link Fase 1: la promo lleva a la página pública del hotel.
    expect(component.notifHref(promo)).toBe('/hotels/3');

    (fixture.nativeElement.querySelector('.notif-bell') as HTMLElement).click();
    fixture.detectChanges();
    const link = fixture.nativeElement.querySelector('.notif-item-sm') as HTMLElement;
    expect(link).not.toBeNull();
    expect((link.getAttribute('href') || '').includes('/hotels/3')).toBe(true);

    component.onNotifClick(promo);
    expect(markRead).toHaveBeenCalledWith('n1');
    expect(component.notifications()[0].unread).toBe(false);
    fixture.destroy();
  });

  it('una notificación transaccional mantiene el link a la reserva y la marca como leída', async () => {
    const markRead = jest.fn(() => of({ id: 'n2', read: true }));
    const { fixture, clientService } = await render('cliente', null, [
      makeClientNotif({
        notificationType: 'guest_confirmed',
        typeLabel: 'Reserva confirmada',
        bookingId: 'BK-001',
      }),
    ], markRead);
    const component = fixture.componentInstance;
    const n = component.notifications()[0];

    expect(component.notifHref(n)).toBe('/account/bookings/BK-001');
    component.onNotifClick(n);
    expect(markRead).toHaveBeenCalledWith('n1');
    fixture.destroy();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it('muestra la campana de notificaciones para el huésped (cliente)', async () => {
    const { fixture } = await render('cliente');
    expect(fixture.nativeElement.querySelector('.notif-bell')).not.toBeNull();
    fixture.destroy();
  });

  it('no muestra la campana para usuarios anónimos', async () => {
    const { fixture } = await render(null);
    expect(fixture.nativeElement.querySelector('.notif-bell')).toBeNull();
    fixture.destroy();
  });

  it('para el huésped carga las notificaciones desde el servicio de cliente (/notifications/my)', async () => {
    const { clientService, systemApi } = await render('cliente');
    expect(clientService.getMyNotifications).toHaveBeenCalled();
    expect(systemApi.getNotifications).not.toHaveBeenCalled();
  });

  it('para super_admin sigue usando la API de notificaciones del sistema', async () => {
    const { clientService, systemApi } = await render('super_admin');
    expect(systemApi.getNotifications).toHaveBeenCalled();
    expect(clientService.getMyNotifications).not.toHaveBeenCalled();
  });

  it('para el huésped usa el nav a ancho completo y un logo ligeramente mayor', async () => {
    const { fixture } = await render('cliente');
    const nav = fixture.nativeElement.querySelector('.top-nav');
    const logo = fixture.nativeElement.querySelector('.brand-logo');

    expect(nav.classList).toContain('top-nav--guest');
    expect(logo.classList).toContain('brand-logo--guest');
    fixture.destroy();
  });

  it('marca el nav del huésped para bajar 3px y alinear su borde inferior', async () => {
    const { fixture } = await render('cliente');
    const nav = fixture.nativeElement.querySelector('.top-nav');

    expect(nav.classList).toContain('top-nav--guest-lowered');
    fixture.destroy();
  });

  it('reemplaza el botón Explorar por enlaces directos en el nav', async () => {
    const { fixture } = await render('cliente');
    const nav = fixture.nativeElement.querySelector('.primary-nav');
    expect(nav.textContent).not.toContain('Explorar');
    const labels = [...nav.querySelectorAll('a.nav-btn .btn-label')].map((a) => (a.textContent as string).trim());
    expect(labels).toContain('Buscar hoteles');
    expect(labels).toContain('Mis Favoritos');
    expect(labels).toContain('Reservas del viajero');
    fixture.destroy();
  });

  it('para el huésped el menú de sesión incluye Mis facturas (/account/billing)', async () => {
    const { fixture } = await render('cliente');
    const items = fixture.componentInstance.sessionMenuItems();
    const labels = items.map((i) => i.label);
    expect(labels).toContain('Mis facturas');
    const item = items.find((i) => i.label === 'Mis facturas');
    expect(item?.href).toBe('/account/billing');
    fixture.destroy();
  });

  it('para el huésped el nav directo incluye Mis facturas (/account/billing)', async () => {
    const { fixture } = await render('cliente');
    const labels = fixture.componentInstance.guestNavItems.map((i) => i.label);
    expect(labels).toContain('Mis facturas');
    const item = fixture.componentInstance.guestNavItems.find((i) => i.label === 'Mis facturas');
    expect(item?.href).toBe('/account/billing');
    fixture.destroy();
  });

  it('no muestra el dropdown de Explorar con su botón desplegable', async () => {
    const { fixture } = await render('cliente');
    const buttons = [...fixture.nativeElement.querySelectorAll('.primary-nav button')];
    expect(buttons.length).toBe(0);
    fixture.destroy();
  });

  it('muestra la foto del huésped en el botón de perfil cuando hay avatar', async () => {
    const { fixture } = await render('cliente', '/api/account/avatar/foto123');
    const img = fixture.nativeElement.querySelector('.session-btn img.session-avatar');
    expect(img).not.toBeNull();
    expect(img.getAttribute('src')).toBe('/api/account/avatar/foto123');
    expect(fixture.nativeElement.querySelector('.session-btn .material-symbols-outlined')).toBeNull();
    fixture.destroy();
  });

  it('sin avatar usa el icono account_circle en el botón de perfil', async () => {
    const { fixture } = await render('cliente', null);
    expect(fixture.nativeElement.querySelector('.session-btn img')).toBeNull();
    expect(fixture.nativeElement.querySelector('.session-btn .material-symbols-outlined')).not.toBeNull();
    fixture.destroy();
  });
});

describe('TopNavComponent — indicador de sección activa (huésped)', () => {
  @Component({ template: '', standalone: true })
  class StubRouteComponent {}

  async function renderAt(url: string, queryParams: Record<string, string> = {}) {
    const systemApi = { getNotifications: jest.fn().mockReturnValue(of({ items: [] })) };
    const clientService = { getMyNotifications: jest.fn().mockReturnValue(of({ items: [], unreadCount: 0 })) };

    await TestBed.configureTestingModule({
      imports: [TopNavComponent],
      providers: [
        provideHttpClient(),
        provideRouter([
          { path: 'search', component: StubRouteComponent },
          { path: 'search/favorites', component: StubRouteComponent },
          { path: 'account/bookings', component: StubRouteComponent },
        ]),
        { provide: AuthService, useValue: makeAuth('cliente') },
        { provide: ThemeService, useValue: themeMock },
        { provide: ReservationsApiService, useValue: {} },
        { provide: NotificationsApiService, useValue: systemApi },
        { provide: ClientNotificationsService, useValue: clientService },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(TopNavComponent);
    const router = TestBed.inject(Router);
    await router.navigate([url], { queryParams });
    fixture.detectChanges();
    return fixture;
  }

  it('solo el enlace de la sección actual lleva la clase is-active (aun con query params)', async () => {
    const fixture = await renderAt('/search', { destination: 'Lima' });
    const active = [...fixture.nativeElement.querySelectorAll('a.nav-link.is-active')];
    expect(active.length).toBe(1);
    expect((active[0].textContent as string)).toContain('Buscar hoteles');
    fixture.destroy();
  });

  it('en Mis Favoritos el activo es ese enlace y no otro (sin falso positivo de /search)', async () => {
    const fixture = await renderAt('/search/favorites');
    const active = [...fixture.nativeElement.querySelectorAll('a.nav-link.is-active')];
    expect(active.length).toBe(1);
    expect((active[0].textContent as string)).toContain('Mis Favoritos');
    fixture.destroy();
  });
});
