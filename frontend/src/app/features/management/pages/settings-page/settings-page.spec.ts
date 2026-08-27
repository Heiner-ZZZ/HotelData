import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { signal } from '@angular/core';
import { of, Subject } from 'rxjs';

import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { AuthService } from '../../../../core/auth/auth.service';
import { ThemeService } from '../../../../core/theme/theme.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { SettingsApiService } from '../../settings/services/settings-api.service';
import type { SettingsViewModel } from '../../settings/models/settings.model';
import { SettingsPageComponent } from './settings-page';

// jsdom no implementa matchMedia; el form de preferencias llama applyTheme() al
// cargar (theme 'system'), que lo necesita para resolver el tema real.
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

describe('SettingsPageComponent — modo CRUD del nav', () => {
  function setup() {
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as never;

    const api = { getSettings: jest.fn(), updateSettings: jest.fn(), changePassword: jest.fn() };
    const toast = { success: jest.fn(), error: jest.fn() };
    const auth = {
      currentUser: signal(null),
      updateAvatar: jest.fn(),
      isAuthenticated: jest.fn(() => true),
      sessionLoaded: jest.fn(() => true),
      invalidateSession: jest.fn(),
      ensureSessionLoaded: jest.fn(() => of(null)),
    };
    // La página delega la aplicación del tema a ThemeService (única fuente de
    // verdad); el mock evita que el servicio real toque BD y localStorage.
    const theme = {
      preference: signal('system'),
      isDark: signal(false),
      toggle: jest.fn(),
      forceLight: jest.fn(),
      setPreference: jest.fn(),
    };

    const settings: SettingsViewModel = { defaultDashboard: '/management', theme: 'system' };
    api.getSettings.mockReturnValue(of(settings));

    TestBed.configureTestingModule({
      imports: [SettingsPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        { provide: AuthService, useValue: auth },
        { provide: ThemeService, useValue: theme },
        { provide: SettingsApiService, useValue: api },
        { provide: ToastService, useValue: toast },
      ],
    });

    const fixture = TestBed.createComponent(SettingsPageComponent);
    fixture.detectChanges();
    // httpResource del nav: responder para evitar requests pendientes.
    TestBed.inject(HttpTestingController).expectOne('/api/admin/navigation').flush({ items: [] });
    fixture.detectChanges();

    return {
      fixture,
      component: fixture.componentInstance,
      mode: TestBed.inject(OperationModeService),
      http: TestBed.inject(HttpTestingController),
      api,
      toast,
      settings,
      theme,
    };
  }

  const flush = () => new Promise<void>((resolve) => setTimeout(resolve, 0));

  function pageEl(ctx: { fixture: { nativeElement: HTMLElement } }) {
    return ctx.fixture.nativeElement as HTMLElement;
  }

  it('parte en modo Solo lectura con los formularios vacíos', () => {
    const ctx = setup();

    expect(ctx.mode.mode()).toBe('read');
    expect(pageEl(ctx).querySelector('.settings-card .unsaved-dot')).toBeNull();
    expect(pageEl(ctx).querySelector('.settings-card .form-status')).toBeNull();
    expect(pageEl(ctx).querySelector('.settings-card')?.classList.contains('mode-active')).toBe(false);
  });

  it('cambia el chip a Editando al escribir en el form de contraseña', () => {
    const ctx = setup();

    ctx.component.passwordForm.controls.currentPassword.setValue('clave-antigua');
    ctx.fixture.detectChanges();

    expect(ctx.mode.mode()).toBe('update');
    expect(ctx.mode.detail()).toBe('Contraseña');
    expect(pageEl(ctx).querySelector('.settings-card .unsaved-dot')).not.toBeNull();
    expect(pageEl(ctx).querySelector('.settings-card .form-status')?.textContent).toContain('cambios sin guardar');
    expect(pageEl(ctx).querySelector('.settings-card')?.classList.contains('mode-active')).toBe(true);
  });

  it('cambia el chip a Editando al modificar preferencias (tema o dashboard)', () => {
    const ctx = setup();

    ctx.component.setTab('preferences');
    ctx.fixture.detectChanges();
    expect(ctx.mode.mode()).toBe('read');

    ctx.component.form.controls.theme.setValue('dark');
    ctx.fixture.detectChanges();

    expect(ctx.mode.mode()).toBe('update');
    expect(ctx.mode.detail()).toBe('Preferencias');
    expect(pageEl(ctx).querySelector('.settings-form .unsaved-dot')).not.toBeNull();
    expect(pageEl(ctx).querySelector('.settings-form .form-status')?.textContent).toContain('cambios sin guardar');
    expect(pageEl(ctx).querySelector('form.settings-form')?.classList.contains('mode-active')).toBe(true);
  });

  it('vuelve a Solo lectura tras guardar preferencias', async () => {
    const ctx = setup();

    ctx.component.setTab('preferences');
    ctx.component.form.controls.theme.setValue('dark');
    ctx.fixture.detectChanges();
    expect(ctx.mode.mode()).toBe('update');

    ctx.api.updateSettings.mockReturnValue(of({ defaultDashboard: '/management', theme: 'dark' }));
    ctx.component.save();
    await flush();
    ctx.fixture.detectChanges();

    expect(ctx.toast.success).toHaveBeenCalledWith('Configuración guardada correctamente.');
    expect(ctx.mode.mode()).toBe('read');
    expect(pageEl(ctx).querySelector('.settings-form .unsaved-dot')).toBeNull();
    expect(pageEl(ctx).querySelector('.settings-form .form-status')).toBeNull();
  });

  it('al cargar/salvar, delega la aplicación del tema a ThemeService (misma fuente de verdad que el icono)', () => {
    const ctx = setup();

    // Al cargar: aplica el tema de la BD sin re-persistir.
    expect(ctx.theme.setPreference).toHaveBeenCalledWith('system', false);
    ctx.theme.setPreference.mockClear();

    ctx.component.setTab('preferences');
    ctx.component.form.controls.theme.setValue('dark');
    ctx.api.updateSettings.mockReturnValue(of({ defaultDashboard: '/management', theme: 'dark' }));
    ctx.component.save();

    // Al guardar: aplica el tema persistido sin doble PUT (persist=false).
    expect(ctx.theme.setPreference).toHaveBeenCalledWith('dark', false);
  });

  it('el modo refleja solo la pestaña activa (Seguridad ↔ Preferencias)', () => {
    const ctx = setup();

    ctx.component.passwordForm.controls.currentPassword.setValue('clave-antigua');
    ctx.fixture.detectChanges();
    expect(ctx.mode.mode()).toBe('update');
    expect(ctx.mode.detail()).toBe('Contraseña');

    // Al pasar a Preferencias (form limpio), el modo vuelve a lectura.
    ctx.component.setTab('preferences');
    ctx.fixture.detectChanges();
    expect(ctx.mode.mode()).toBe('read');

    // La edición de contraseña sigue viva al volver a Seguridad.
    ctx.component.setTab('security');
    ctx.fixture.detectChanges();
    expect(ctx.mode.mode()).toBe('update');
    expect(ctx.mode.detail()).toBe('Contraseña');
  });
});
