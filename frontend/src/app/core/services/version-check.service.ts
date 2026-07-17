import { inject, Injectable, signal, DestroyRef } from '@angular/core';
import { HttpClient, HttpContext } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { interval, startWith, switchMap } from 'rxjs';

import { BYPASS_BASE_URL } from '../api/api-context.tokens';

const VERSION_URL = '/assets/version.json';
const POLL_INTERVAL_MS = 30_000;
const LS_KEY = 'hd-app-version';

@Injectable({ providedIn: 'root' })
export class VersionCheckService {
  private readonly http = inject(HttpClient);
  private readonly destroyRef = inject(DestroyRef);

  /** True when a new version is detected and the user should reload */
  readonly updateAvailable = signal(false);

  /** Latest fetched build timestamp (cached so applyUpdate can skip a second request) */
  private latestBuild = '';

  constructor() {
    this._startPolling();
  }

  /** Start polling for version changes. Auto-starts on service init; public for manual restart if needed. */
  startPolling(): void {
    this._startPolling();
  }

  private _startPolling(): void {
    interval(POLL_INTERVAL_MS)
      .pipe(
        startWith(0),
        switchMap(() =>
          this.http.get<{ build: string }>(VERSION_URL, {
            headers: { 'Cache-Control': 'no-cache' },
            params: { _t: Date.now() },
            context: new HttpContext().set(BYPASS_BASE_URL, true),
          }),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (res) => {
          this.latestBuild = res.build;
          const stored = localStorage.getItem(LS_KEY);
          if (!stored) {
            localStorage.setItem(LS_KEY, res.build);
            return;
          }
          if (stored !== res.build) {
            this.updateAvailable.set(true);
          }
        },
        error: () => {
          // Network error — ignore silently
        },
      });
  }

  /** User clicked reload or dismiss-accept — store new version and reload */
  applyUpdate(): void {
    if (this.latestBuild) {
      localStorage.setItem(LS_KEY, this.latestBuild);
    }
    window.location.reload();
  }

  /** Dismiss banner permanently until next deployment (accept current version) */
  dismiss(): void {
    if (this.latestBuild) {
      localStorage.setItem(LS_KEY, this.latestBuild);
    }
    this.updateAvailable.set(false);
  }
}
