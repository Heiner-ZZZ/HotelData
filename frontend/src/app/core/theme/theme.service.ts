import { computed, effect, inject, Injectable, signal } from '@angular/core';

import { AuthService } from '../auth/auth.service';
import { SettingsApiService } from '../../features/management/settings/services/settings-api.service';

/** Preferencia de tema canónica. La pantalla de Configuración ofrece las
 *  tres; el icono del nav solo escribe 'light' | 'dark' (las dos primeras). */
export type ThemePreference = 'system' | 'light' | 'dark';

const STORAGE_KEY = 'hoteldata-theme';
const PREFERENCE_KEY = 'hoteldata-theme-preference';

function resolveDark(pref: ThemePreference): boolean {
  if (pref === 'dark') return true;
  if (pref === 'light') return false;
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

/**
 * Única fuente de verdad del tema visual.
 *
 * Para usuarios autenticados la fuente es la BD: se lee con
 * `GET /api/settings` y se persiste con `PUT /api/settings` — el MISMO
 * endpoint que usa la pantalla de Configuración. Así el icono del nav y el
 * select de Configuración nunca divergen (antes el icono escribía solo en
 * localStorage y la config en la BD, y cada sección "adivinaba" a cuál
 * hacerle caso). localStorage queda como cache local y fallback de
 * invitados / primer pintado.
 */
@Injectable({
  providedIn: 'root',
})
export class ThemeService {
  /** Preferencia canónica ('system' | 'light' | 'dark'). */
  readonly preference = signal<ThemePreference>('system');

  /** Ruta pública /welcome: siempre modo claro, sin importar la preferencia. */
  private readonly lightOverride = signal(false);

  /** Estado efectivo renderizado (respeta el override de /welcome). */
  readonly isDark = computed<boolean>(() =>
    this.lightOverride() ? false : resolveDark(this.preference()),
  );

  private readonly auth = inject(AuthService);
  private readonly settingsApi = inject(SettingsApiService);

  constructor() {
    // Primer pintado: cache local (sin red, sin esperar la sesión).
    this.applyLocal(this.readLocalPreference());

    // Cuando la sesión resuelve, la BD manda (misma fuente que Configuración).
    // En logout / invitados se vuelve al cache local.
    effect(() => {
      if (this.auth.isAuthenticated()) {
        this.loadFromServer();
      } else {
        this.applyLocal(this.readLocalPreference());
      }
    });
  }

  /** El icono del nav alterna claro/oscuro y persiste por el MISMO endpoint
   *  de Configuración (PUT /api/settings). Nunca escribe 'system': el modo
   *  sistema se resuelve en la lectura y el primer click lo vuelve explícito. */
  toggle(): void {
    this.setPreference(this.isDark() ? 'light' : 'dark');
  }

  /** Aplica la preferencia y, salvo `persist=false`, la guarda en la BD
   *  (mismo endpoint que el save de Configuración). `persist=false` es para
   *  la pantalla de Configuración, que ya persiste en su propio save. */
  setPreference(pref: ThemePreference, persist = true): void {
    this.applyLocal(pref);
    if (persist && this.auth.isAuthenticated()) {
      this.settingsApi
        .updateSettings({ theme: pref })
        // Optimista: el cambio ya está aplicado; si la BD rechaza, la próxima
        // carga re-sincroniza desde el servidor.
        .subscribe({ error: () => undefined });
    }
  }

  /** Fuerza modo claro mientras la ruta esté montada (landing /welcome). */
  forceLight(enabled: boolean): void {
    this.lightOverride.set(enabled);
    this.syncDom();
  }

  // ── Privados ──────────────────────────────────────────────────────────

  private applyLocal(pref: ThemePreference): void {
    this.preference.set(pref);
    this.cacheLocal(pref);
    this.syncDom();
  }

  private cacheLocal(pref: ThemePreference): void {
    try {
      localStorage.setItem(PREFERENCE_KEY, pref);
      localStorage.setItem(STORAGE_KEY, resolveDark(pref) ? 'dark' : 'light');
    } catch {
      /* localStorage no disponible */
    }
  }

  private syncDom(): void {
    document.documentElement.setAttribute(
      'data-theme',
      this.isDark() ? 'dark' : 'light',
    );
  }

  private readLocalPreference(): ThemePreference {
    try {
      const pref = localStorage.getItem(PREFERENCE_KEY);
      if (pref === 'light' || pref === 'dark' || pref === 'system') return pref;
    } catch {
      /* localStorage no disponible */
    }
    return 'system';
  }

  private loadFromServer(): void {
    this.settingsApi
      .getSettings()
      .subscribe({
        next: (s) => this.applyLocal(s.theme as ThemePreference),
        // Error silencioso: se mantiene el cache local.
        error: () => undefined,
      });
  }
}
