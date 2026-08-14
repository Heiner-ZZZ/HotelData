import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, NavigationEnd, Router, convertToParamMap } from '@angular/router';
import { of, Subject } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { ThemeService } from '../../../core/theme/theme.service';
import { PropertyContextService } from '../../../shared/services/property-context.service';
import { SidebarNavComponent } from './sidebar-nav';

describe('SidebarNavComponent (auto-expand del árbol)', () => {
  // Árbol mínimo que reproduce el bug de prefix-match: `gestion.pms` tiene
  // href "/management" (prefijo de todo /management/*), así que el viejo
  // `_findPath` (primer match DFS) lo elegía antes que `gestion.reservas`.
  const NAV_ITEMS = [
    { slug: 'gestion', parentSlug: null, position: 10, nodeType: 'container', label: 'Gestión', href: null, icon: 'dashboard', visible: true, permissionId: null, permissionCode: null, horizontalMenu: false },
    { slug: 'gestion.pms', parentSlug: 'gestion', position: 10, nodeType: 'container', label: 'Dashboard', href: '/management', icon: 'dashboard', visible: true, permissionId: null, permissionCode: null, horizontalMenu: false },
    { slug: 'gestion.reservas', parentSlug: 'gestion', position: 20, nodeType: 'container', label: 'Reservas', href: '/management/reservations', icon: 'book_online', visible: true, permissionId: null, permissionCode: null, horizontalMenu: false },
    { slug: 'gestion.reservas.tarifas', parentSlug: 'gestion.reservas', position: 20, nodeType: 'leaf', label: 'Tarifas', href: '/management/reservations/tarifas', icon: 'sell', visible: true, permissionId: null, permissionCode: null, horizontalMenu: false },
    { slug: 'sistema', parentSlug: null, position: 20, nodeType: 'container', label: 'Sistema', href: null, icon: 'admin_panel_settings', visible: true, permissionId: null, permissionCode: null, horizontalMenu: false },
    { slug: 'sistema.usuarios', parentSlug: 'sistema', position: 10, nodeType: 'leaf', label: 'Usuarios', href: '/system/users', icon: 'people', visible: true, permissionId: null, permissionCode: null, horizontalMenu: false },
  ];

  function setup() {
    const events = new Subject<unknown>();
    const router = {
      events: events.asObservable(),
      url: '/',
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const auth = {
      ensureSessionLoaded: jest.fn(() => of({})),
      currentUser: signal(null),
      hasPermission: jest.fn(() => true),
    } as unknown as AuthService;
    const theme = {
      isDark: jest.fn(() => false),
      toggle: jest.fn(),
    } as unknown as ThemeService;
    const propCtx = {
      currentPropId: jest.fn(() => 0),
    } as unknown as PropertyContextService;

    TestBed.configureTestingModule({
      imports: [SidebarNavComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { paramMap: convertToParamMap({}), queryParamMap: convertToParamMap({}) },
            paramMap: of(convertToParamMap({})),
            queryParamMap: of(convertToParamMap({})),
          },
        },
        { provide: AuthService, useValue: auth },
        { provide: ThemeService, useValue: theme },
        { provide: PropertyContextService, useValue: propCtx },
      ],
    });

    const fixture = TestBed.createComponent(SidebarNavComponent);
    const http = TestBed.inject(HttpTestingController);
    return { fixture, component: fixture.componentInstance, http, router, events };
  }

  async function loadNav(ctx: { http: HttpTestingController; fixture: { detectChanges(): void } }) {
    ctx.http.expectOne('/api/admin/navigation').flush({ items: NAV_ITEMS });
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();
  }

  function slugs(component: SidebarNavComponent): string[] {
    return [...component.openNodes()];
  }

  it('NO expande secciones para páginas fuera del árbol (p.ej. /management/settings)', async () => {
    const ctx = setup();
    ctx.fixture.detectChanges();
    ctx.router.url = '/management/settings';
    await loadNav(ctx);

    // Preferencias de cuenta no pertenece al árbol de navegación: no debe
    // auto-expandir Gestión (el prefijo /management de gestion.pms no cubre
    // la página, no tiene descendientes con ese camino).
    expect(slugs(ctx.component)).not.toContain('gestion');
    expect(slugs(ctx.component)).not.toContain('gestion.pms');
  });

  it('expande los ancestros del href más específico (no el prefijo /management)', async () => {
    const ctx = setup();
    ctx.fixture.detectChanges();
    ctx.router.url = '/management/reservations/tarifas';
    await loadNav(ctx);

    expect(slugs(ctx.component)).toEqual(expect.arrayContaining(['gestion', 'gestion.reservas']));
  });

  it('mergea las secciones abiertas manualmente al navegar (no las cierra)', async () => {
    const ctx = setup();
    ctx.fixture.detectChanges();
    ctx.router.url = '/management/reservations/tarifas';
    await loadNav(ctx);
    expect(slugs(ctx.component)).toEqual(expect.arrayContaining(['gestion', 'gestion.reservas']));

    // Abrir manualmente otra sección que NO está en el camino activo.
    ctx.component.toggle('sistema');
    expect(slugs(ctx.component)).toContain('sistema');

    // Navegar a una ruta distinta (SPA).
    ctx.router.url = '/management';
    ctx.events.next(new NavigationEnd(2, '/management', '/management'));
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();

    // 'sistema' sigue abierto: el auto-expand mergea, no reemplaza.
    expect(slugs(ctx.component)).toContain('sistema');
  });

  it('expone aria-expanded como booleano (no como string literal)', async () => {
    const ctx = setup();
    ctx.fixture.detectChanges();
    await loadNav(ctx);

    const header = ctx.fixture.nativeElement.querySelector('.section-header');
    const value = header?.getAttribute('aria-expanded');
    expect(['true', 'false']).toContain(value);
    expect(value).not.toBe('isOpen(root.slug)');
  });
});
