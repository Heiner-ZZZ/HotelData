import { Location } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { DestroyRef, effect, inject, Injectable, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router } from '@angular/router';
import { catchError, filter, map, of } from 'rxjs';

import { getErrorStatus } from '../utils/http-error.util';
import { API_CONFIG } from '../../core/api/api.config';
import { AuthService } from '../../core/auth/auth.service';

export interface PropertyContextDto {
  mode: string;
  assigned_properties: { prop_id: number; label: string }[];
  default_prop_id: number;
}

/** Management paths that are global and should never carry a `prop_id` query param. */
export const GLOBAL_MANAGEMENT_PATHS = [
  '/management/profile',
  '/management/settings',
  '/management/audit-log',
  '/management/reports',
] as const;

/** Check if a path (or any of its sub-paths) belongs to the global management section. */
export function isGlobalManagementPath(path: string): boolean {
  return GLOBAL_MANAGEMENT_PATHS.some((global) => path === global || path.startsWith(`${global}/`));
}

@Injectable({ providedIn: 'root' })
export class PropertyContextService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly location = inject(Location);
  private readonly destroyRef = inject(DestroyRef);

  readonly currentPropId = signal(0);
  readonly currentPropLabel = signal('');
  readonly currentPropLabelShort = signal('');

  readonly currentCurrency = signal('USD');
  readonly currentAcceptedCurrencies = signal<string[]>(['USD']);

  /**
   * The default property ID assigned to this user (single-hotel mode).
   * Never cleared by clear() — survives page-level resets so effects
   * and NavigationEnd listeners can always re-inject the correct prop_id.
   */
  readonly defaultPropId = signal(0);

  /** The property access mode for the current user. */
  readonly mode = signal<'all' | 'single' | 'multi' | 'none'>('all');
  /** Assigned properties (only populated in single/multi mode). */
  readonly assignedProperties = signal<{ propId: number; label: string }[]>([]);
  /** True when the context has been loaded from the backend. */
  readonly ready = signal(false);

  /** Whether the current user has a single-hotel restriction (mode=single). */
  readonly singleHotelMode = signal(false);

  /** Guard against multiple concurrent loads. */
  private loading = false;

  constructor() {
    // Defer context load until auth session is confirmed.
    // When isAuthenticated() becomes true, load the context.
    // When isAuthenticated() becomes false (logout), reset and wait for next login.
    effect(() => {
      const authenticated = this.auth.isAuthenticated();
      const sessionLoaded = this.auth.sessionLoaded();

      if (sessionLoaded && authenticated && !this.loading && !this.ready()) {
        this.loadContext();
      }

      if (sessionLoaded && !authenticated) {
        this.resetState();
      }
    });

    // When context becomes ready in single-hotel mode, inject prop_id into URL.
    // Uses Location.replaceState (sync) to avoid race conditions from async router.navigate.
    effect(() => {
      if (this.ready() && this.singleHotelMode()) {
        this._ensurePropIdInUrl(this.defaultPropId());
      }
    });

    // After EVERY navigation (including sidebar links that strip query params),
    // re-inject prop_id if missing. Uses defaultPropId which survives clear().
    this.router.events
      .pipe(
        filter((e): e is NavigationEnd => e instanceof NavigationEnd),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(() => {
        if (!this.ready()) return;
        if (this.singleHotelMode()) {
          this._ensurePropIdInUrl(this.defaultPropId());
        } else {
          this._syncCurrentPropIdFromUrl();
        }
      });
  }

  /**
   * Force a reload of the property context.
   * Useful after login or after hotel assignments change.
   */
  reload(): void {
    this.loading = false;
    this.loadContext();
  }

  private loadContext(): void {
    if (this.loading) return;
    // Property context is only meaningful on management routes. The DI graph
    // wires PropertyContextService into the root injector, so any shell that
    // activates (account, system, ownership, public) would otherwise fire the
    // same /api/management/properties/context call and produce 401/403 noise on
    // guest-side paths like /account/bookings. Restrict the call to /management/*.
    const url = this.router.url || '/';
    // Strip query string and hash fragment — `router.url` returns the full URL
    // (e.g. `/management?prop_id=1`), so naïve `startsWith('/management/')` misses
    // bare `/management?prop_id=1` (the next char is `?`, not `/`). Same split
    // pattern as `_ensurePropIdInUrl` further down in this class.
    const pathOnly = url.split('?')[0].split('#')[0];
    const isManagementRoute = pathOnly === '/management' || pathOnly.startsWith('/management/');
    if (!isManagementRoute) return;
    this.loading = true;

    this.http
      .get<PropertyContextDto>(`${this.apiConfig.baseUrl}/management/properties/context`, {
        withCredentials: true,
      })
      .pipe(
        map((dto) => ({
          mode: dto.mode as 'all' | 'single' | 'multi' | 'none',
          assignedProperties: dto.assigned_properties.map((p) => ({
            propId: p.prop_id,
            label: p.label,
          })),
          defaultPropId: dto.default_prop_id,
        })),
        catchError((err: unknown) => {
          // getErrorStatus cubre HttpErrorResponse (tests) y ApiError del interceptor (vivo).
          const status = getErrorStatus(err) ?? null;
          // 401/403 means auth token expired or not yet available — don't cache fallback,
          // let the effect retry when auth state changes.
          if (status === 401 || status === 403) {
            console.warn('[PropertyContext] Auth required — waiting for session');
            this.loading = false;
            // Throw to skip the subscribe handler — ready stays false, effect will retry
            throw err;
          }
          // For other errors (network, server), use fallback so UI doesn't hang forever
          console.warn('[PropertyContext] Error cargando contexto, usando fallback all:', status);
          return of({
            mode: 'all' as const,
            assignedProperties: [] as { propId: number; label: string }[],
            defaultPropId: 0,
          });
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (ctx) => {
          this.applyContext(ctx);
          this.loading = false;
        },
        error: (err: unknown) => {
          this.loading = false;
          // On 401/403, invalidate the session so the auth effect triggers
          // resetState → re-login → reload. This guarantees recovery even if
          // the auth HTTP interceptor hasn't fired yet for this call path.
          const status = getErrorStatus(err);
          if (status === 401 || status === 403) {
            this.auth.invalidateSession();
          }
        },
      });
  }

  private applyContext(ctx: {
    mode: 'all' | 'single' | 'multi' | 'none';
    assignedProperties: { propId: number; label: string }[];
    defaultPropId: number;
  }): void {
    this.mode.set(ctx.mode);
    this.assignedProperties.set(ctx.assignedProperties);
    this.singleHotelMode.set(ctx.mode === 'single');

    if (ctx.mode === 'single' && ctx.defaultPropId) {
      this.defaultPropId.set(ctx.defaultPropId);
      const prop = ctx.assignedProperties.find((p) => p.propId === ctx.defaultPropId);
      if (prop) {
        this.setProperty(prop.propId, prop.label);
      }
    }

    this.ready.set(true);

    // In 'all'/'multi' mode the URL is the source of truth for the active property.
    // Sync currentPropId from the query string after context is ready so management
    // pages respect ?prop_id=1 even for superadmins.
    this._syncCurrentPropIdFromUrl();
  }

  /** Read ?prop_id from the current URL and update currentPropId accordingly. */
  private _syncCurrentPropIdFromUrl(): void {
    try {
      const url = this.router.url;
      const qs = new URLSearchParams(url.split('?')[1] || '');
      const propIdParam = qs.get('prop_id');
      if (!propIdParam) return;
      const propId = Number(propIdParam);
      if (Number.isNaN(propId) || propId <= 0) return;

      const mode = this.mode();
      if (mode === 'single') {
        // Single mode ignores URL prop_id unless it matches the assigned property
        if (propId !== this.defaultPropId()) return;
      }
      if (mode === 'multi') {
        // Multi mode only allows assigned properties
        const allowed = this.assignedProperties().some((p) => p.propId === propId);
        if (!allowed) return;
      }
      // 'all' mode accepts any positive prop_id from the URL
      this.currentPropId.set(propId);
      const assigned = this.assignedProperties().find((p) => p.propId === propId);
      if (assigned) {
        this.currentPropLabel.set(assigned.label);
        const short = assigned.label.length > 18 ? assigned.label.slice(0, 16) + '\u2026' : assigned.label;
        this.currentPropLabelShort.set(short);
      }
    } catch {
      // Router may not be ready during bootstrap — safe to ignore
    }
  }

  private resetState(): void {
    this.ready.set(false);
    this.loading = false;
    this.mode.set('all');
    this.assignedProperties.set([]);
    this.singleHotelMode.set(false);
    this.defaultPropId.set(0);
    this.currentPropId.set(0);
    this.currentPropLabel.set('');
    this.currentPropLabelShort.set('');
    this.currentCurrency.set('USD');
    this.currentAcceptedCurrencies.set(['USD']);
  }

  setCurrency(currency: string, acceptedCurrencies: string[] = []): void {
    this.currentCurrency.set(currency);
    this.currentAcceptedCurrencies.set(acceptedCurrencies.length ? acceptedCurrencies : [currency]);
  }

  /**
   * For single-hotel mode, ensure ?prop_id=X is in the current URL.
   * Uses router.navigateByUrl to trigger a proper Angular navigation,
   * which updates queryParamMap so page components see the prop_id.
   * Only injects if propId > 0 and prop_id is not already in the URL.
   */
  private _ensurePropIdInUrl(propId: number): void {
    if (propId <= 0) return;
    try {
      const url = this.router.url;
      const path = url.split('?')[0];
      if (!path.startsWith('/management') || isGlobalManagementPath(path) || url.includes('prop_id=')) return;

      const qs = new URLSearchParams(url.split('?')[1] || '');
      qs.set('prop_id', String(propId));
      void this.router.navigateByUrl(`${path}?${qs.toString()}`, { replaceUrl: true });
    } catch {
      // Router may not be ready during initial bootstrap — safe to ignore
    }
  }

  setProperty(propId: number, label: string): void {
    this.currentPropId.set(propId);
    this.currentPropLabel.set(label);
    const short = label.length > 18 ? label.slice(0, 16) + '\u2026' : label;
    this.currentPropLabelShort.set(short);
    // Also ensure URL has prop_id when set manually (e.g. from property selector)
    if (this.singleHotelMode()) {
      this._ensurePropIdInUrl(propId);
    }
  }

  clear(): void {
    this.currentPropId.set(0);
    this.currentPropLabel.set('');
    this.currentPropLabelShort.set('');
  }
}
