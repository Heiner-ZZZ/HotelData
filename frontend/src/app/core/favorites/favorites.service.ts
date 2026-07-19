import { httpResource } from '@angular/common/http';
import { HttpClient } from '@angular/common/http';
import { effect, inject, Injectable, signal } from '@angular/core';

import { API_CONFIG } from '../api/api.config';
import { AuthService } from '../auth/auth.service';

@Injectable({ providedIn: 'root' })
export class FavoritesService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);
  private readonly apiConfig = inject(API_CONFIG);

  private readonly _ids = signal<Set<number>>(new Set());
  readonly loaded = signal(false);

  /** httpResource for GET /api/account/favorites — reactive, auto-fetches when authenticated. */
  private readonly favoritesRes = httpResource<{ ok: boolean; favorites: number[] }>(() =>
    this.auth.isAuthenticated()
      ? `${this.apiConfig.baseUrl}/account/favorites`
      : undefined,
  );

  readonly favoriteIds = this._ids.asReadonly();

  constructor() {
    // Sync httpResource value → local Set signal
    effect(() => {
      const data = this.favoritesRes.value();
      if (data?.favorites) {
        this._ids.set(new Set(data.favorites));
        this.loaded.set(true);
      }
    });
    // Clear favorites when user logs out
    effect(() => {
      if (!this.auth.isAuthenticated() && this.auth.sessionLoaded()) {
        this._ids.set(new Set());
        this.loaded.set(false);
      }
    });
  }

  /** Toggle a hotel's favorite status. Returns `false` if user not authenticated. */
  toggle(hotelId: number): boolean {
    if (!this.auth.isAuthenticated()) return false;

    const current = this._ids();
    const wasFavorited = current.has(hotelId);

    // ── Optimistic update ──
    const next = new Set(current);
    wasFavorited ? next.delete(hotelId) : next.add(hotelId);
    this._ids.set(next);

    // ── Fire-and-forget API call ──
    const url = `${this.apiConfig.baseUrl}/account/favorites`;
    const req = wasFavorited
      ? this.http.delete(`${url}/${hotelId}`, { withCredentials: true })
      : this.http.post(url, { hotel_id: hotelId }, { withCredentials: true });

    req.subscribe({
      error: () => {
        // Revert on error
        this._ids.set(current);
      },
    });

    return true;
  }
}
