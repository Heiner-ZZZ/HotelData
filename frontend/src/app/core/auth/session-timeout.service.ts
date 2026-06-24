import { HttpClient } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter, Subscription, timer } from 'rxjs';

import { API_CONFIG } from '../api/api.config';

const STORAGE_KEY = 'hoteldata-session-timeout';

@Injectable({ providedIn: 'root' })
export class SessionTimeoutService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly apiConfig = inject(API_CONFIG);

  private activityTimer: ReturnType<typeof setTimeout> | null = null;
  private activitySubscription: Subscription | null = null;
  private routeSubscription: Subscription | null = null;
  private heartbeatSubscription: Subscription | null = null;
  private timeoutMs = 60 * 60 * 1000;
  private readonly heartbeatIntervalMs = 60_000; // 1 minute

  /** Signal exposed to UI components to show a warning banner */
  readonly sessionExpiringSoon = signal(false);

  start(): void {
    const stored = localStorage.getItem(STORAGE_KEY);
    const minutes = stored ? Number(stored) : 60;
    this.timeoutMs = minutes * 60 * 1000;

    this.stop();
    this.resetTimer();
    this.startHeartbeat();

    this.activitySubscription = this.listen('mousemove keydown click scroll touchstart', () => this.resetTimer());
    this.routeSubscription = this.router.events.pipe(filter(e => e instanceof NavigationEnd)).subscribe(() => this.resetTimer());
  }

  setDuration(minutes: number): void {
    localStorage.setItem(STORAGE_KEY, String(minutes));
    this.timeoutMs = minutes * 60 * 1000;
    if (this.activityTimer) this.resetTimer();
  }

  /** Send an immediate heartbeat to the backend. */
  ping(): void {
    this.http
      .post<{ ok: boolean; inactivity_timeout_minutes?: number }>(
        `${this.apiConfig.baseUrl}/auth/heartbeat`,
        {},
        { withCredentials: true }
      )
      .subscribe({
        next: (res) => {
          if (res.inactivity_timeout_minutes) {
            const backendTimeout = res.inactivity_timeout_minutes * 60 * 1000;
            if (backendTimeout !== this.timeoutMs) {
              this.setDuration(res.inactivity_timeout_minutes);
            }
          }
        },
        error: () => {
          // Ignore heartbeat failures — the auth interceptor will handle 401s
        },
      });
  }

  stop(): void {
    if (this.activityTimer) { clearTimeout(this.activityTimer); this.activityTimer = null; }
    if (this.activitySubscription) { this.activitySubscription.unsubscribe(); this.activitySubscription = null; }
    if (this.routeSubscription) { this.routeSubscription.unsubscribe(); this.routeSubscription = null; }
    if (this.heartbeatSubscription) { this.heartbeatSubscription.unsubscribe(); this.heartbeatSubscription = null; }
    this.sessionExpiringSoon.set(false);
  }

  private startHeartbeat(): void {
    this.heartbeatSubscription = timer(30_000, this.heartbeatIntervalMs).subscribe(() => {
      this.ping();
    });
  }

  private resetTimer(): void {
    if (this.activityTimer) clearTimeout(this.activityTimer);
    // Show warning when 10% of the timeout is remaining
    const warningThreshold = this.timeoutMs * 0.9;
    this.activityTimer = setTimeout(() => {
      this.sessionExpiringSoon.set(true);
      // Final countdown: logout after the remaining 10%
      setTimeout(() => this.logout(), this.timeoutMs * 0.1);
    }, warningThreshold);
  }

  private logout(): void {
    this.stop();
    window.location.href = '/auth/logout';
  }

  private listen(events: string, handler: () => void): Subscription {
    const onEvent = () => handler();
    events.split(' ').forEach(ev => window.addEventListener(ev, onEvent, { passive: true }));
    return new Subscription(() => events.split(' ').forEach(ev => window.removeEventListener(ev, onEvent)));
  }
}
