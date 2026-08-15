import { provideHttpClient } from '@angular/common/http';
import {
  HttpTestingController,
  provideHttpClientTesting,
} from '@angular/common/http/testing';
import { ApplicationRef, computed, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { AuthService } from '../auth/auth.service';
import { ThemeService } from './theme.service';

// jsdom no implementa matchMedia; resolveDark('system') lo necesita.
if (!window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}

const PREFERENCE_KEY = 'hoteldata-theme-preference';
const STORAGE_KEY = 'hoteldata-theme';

/** Mock de AuthService con una señal de autenticación que podemos voltear
 *  para probar la carga desde la BD cuando la sesión se resuelve. */
function makeAuth(initial: boolean) {
  const authState = signal({
    authenticated: initial,
    user: null,
    session: null,
    homeHref: null,
    permissionCodes: [] as string[],
  });
  return {
    authState: authState.asReadonly(),
    isAuthenticated: computed(() => authState().authenticated),
    setAuth(v: boolean) {
      authState.set({
        authenticated: v,
        user: null,
        session: null,
        homeHref: null,
        permissionCodes: [],
      });
    },
  } as unknown as AuthService & { setAuth(v: boolean): void };
}

describe('ThemeService — única fuente de verdad (BD vía /api/settings)', () => {
  let theme: ThemeService;
  let auth: ReturnType<typeof makeAuth>;
  let http: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
    auth = makeAuth(false);

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: AuthService, useValue: auth },
      ],
    });
    theme = TestBed.inject(ThemeService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
  });

  it('toggle() persiste claro/oscuro por el MISMO endpoint de configuración (PUT /api/settings)', () => {
    localStorage.setItem(PREFERENCE_KEY, 'light');
    theme.setPreference('light', false);
    auth.setAuth(true);

    theme.toggle();
    expect(theme.isDark()).toBe(true);
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    const put = http.expectOne((r) => r.method === 'PUT' && r.url.endsWith('/api/settings'));
    expect(put.request.body).toEqual({ theme: 'dark' });
    put.flush({ default_dashboard: '/management', theme: 'dark' });

    theme.toggle();
    expect(theme.isDark()).toBe(false);
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    const put2 = http.expectOne((r) => r.method === 'PUT' && r.url.endsWith('/api/settings'));
    expect(put2.request.body).toEqual({ theme: 'light' });
    put2.flush({ default_dashboard: '/management', theme: 'light' });
  });

  it('setPreference(pref, false) aplica sin PUT (la config ya persiste en su save)', () => {
    auth.setAuth(true);
    theme.setPreference('dark', false);
    expect(theme.isDark()).toBe(true);
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    http.expectNone((r) => r.method === 'PUT');
  });

  it('al autenticarse, la BD (GET /api/settings) manda sobre el cache local', async () => {
    localStorage.setItem(PREFERENCE_KEY, 'light');
    auth.setAuth(true);
    // El effect que reacciona a la sesión corre en un tick de la app.
    TestBed.inject(ApplicationRef).tick();

    const get = http.expectOne((r) => r.method === 'GET' && r.url.endsWith('/api/settings'));
    get.flush({ default_dashboard: '/management', theme: 'dark' });

    expect(theme.isDark()).toBe(true);
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    expect(localStorage.getItem(PREFERENCE_KEY)).toBe('dark');
  });

  it('usuario anónimo: toggle solo escribe localStorage, sin llamada HTTP', () => {
    localStorage.setItem(PREFERENCE_KEY, 'dark');
    theme.setPreference('dark', false);

    theme.toggle();
    expect(theme.isDark()).toBe(false);
    expect(localStorage.getItem(PREFERENCE_KEY)).toBe('light');
    expect(localStorage.getItem(STORAGE_KEY)).toBe('light');
    http.expectNone((r) => r.method === 'PUT' || r.method === 'GET');
  });

  it('forceLight() fuerza claro aun con preferencia oscura y se libera al desactivar', () => {
    localStorage.setItem(PREFERENCE_KEY, 'dark');
    theme.setPreference('dark', false);

    theme.forceLight(true);
    expect(theme.isDark()).toBe(false);
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');

    theme.forceLight(false);
    expect(theme.isDark()).toBe(true);
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
  });
});
