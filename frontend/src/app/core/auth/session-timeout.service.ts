import { inject, Injectable } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter, Subscription } from 'rxjs';

const STORAGE_KEY = 'hoteldata-session-timeout';

@Injectable({ providedIn: 'root' })
export class SessionTimeoutService {
  private readonly router = inject(Router);

  private activityTimer: ReturnType<typeof setTimeout> | null = null;
  private activitySubscription: Subscription | null = null;
  private routeSubscription: Subscription | null = null;
  private timeoutMs = 60 * 60 * 1000;

  start(): void {
    const stored = localStorage.getItem(STORAGE_KEY);
    const minutes = stored ? Number(stored) : 60;
    this.timeoutMs = minutes * 60 * 1000;

    this.stop();
    this.resetTimer();

    this.activitySubscription = this.listen('mousemove keydown click scroll touchstart', () => this.resetTimer());
    this.routeSubscription = this.router.events.pipe(filter(e => e instanceof NavigationEnd)).subscribe(() => this.resetTimer());
  }

  setDuration(minutes: number): void {
    localStorage.setItem(STORAGE_KEY, String(minutes));
    this.timeoutMs = minutes * 60 * 1000;
    if (this.activityTimer) this.resetTimer();
  }

  stop(): void {
    if (this.activityTimer) { clearTimeout(this.activityTimer); this.activityTimer = null; }
    if (this.activitySubscription) { this.activitySubscription.unsubscribe(); this.activitySubscription = null; }
    if (this.routeSubscription) { this.routeSubscription.unsubscribe(); this.routeSubscription = null; }
  }

  private resetTimer(): void {
    if (this.activityTimer) clearTimeout(this.activityTimer);
    this.activityTimer = setTimeout(() => this.logout(), this.timeoutMs);
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
