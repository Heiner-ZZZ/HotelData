import { inject, Injectable, signal, DestroyRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { interval, startWith, switchMap } from 'rxjs';

const VERSION_URL = '/assets/version.json';
const POLL_INTERVAL_MS = 30_000;
const LS_KEY = 'hd-app-version';

@Injectable({ providedIn: 'root' })
export class VersionCheckService {
  private readonly http = inject(HttpClient);

  /** True when a new version is detected and the user should reload */
  readonly updateAvailable = signal(false);

  /** Latest fetched build timestamp (cached so applyUpdate can skip a second request) */
  private latestBuild = '';

  /** Start polling for version changes. Call once from AppComponent constructor. */
  startPolling(destroyRef: DestroyRef): void {
    interval(POLL_INTERVAL_MS)
      .pipe(
        startWith(0),
        switchMap(() =>
          this.http.get<{ build: string }>(VERSION_URL, {
            headers: { 'Cache-Control': 'no-cache' },
            params: { _t: Date.now() }, // cache-bust query param
          }),
        ),
        takeUntilDestroyed(destroyRef),
      )
      .subscribe({
        next: (res) => {
          this.latestBuild = res.build;
          const stored = localStorage.getItem(LS_KEY);
          if (!stored) {
            // First visit — store version silently
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
