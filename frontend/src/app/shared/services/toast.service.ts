import { Injectable, signal } from '@angular/core';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastMessage {
  id: string;
  message: string;
  type: ToastType;
  duration: number;
}

@Injectable({ providedIn: 'root' })
export class ToastService {
  readonly toasts = signal<ToastMessage[]>([]);
  private counter = 0;
  private readonly recentToastAt = new Map<string, number>();

  /** Show a toast notification. Auto-dismisses after `duration` ms (default 5500). */
  show(message: string, type: ToastType = 'info', duration = 5500): string {
    // Several subscribers can observe the same failed HTTP request. Suppress
    // only bursts of the same notification; after the short window, a real
    // repeated action should still be visible to the user.
    const key = `${type}:${message}`;
    const now = Date.now();
    const previousAt = this.recentToastAt.get(key) ?? 0;
    if (now - previousAt < 1000) {
      const existing = this.toasts().find(
        (toast) => toast.message === message && toast.type === type,
      );
      if (existing) return existing.id;
    }
    this.recentToastAt.set(key, now);
    setTimeout(() => {
      if (this.recentToastAt.get(key) === now) {
        this.recentToastAt.delete(key);
      }
    }, 1000);

    const id = `toast-${++this.counter}`;
    this.toasts.update((list) => [...list, { id, message, type, duration }]);

    if (duration > 0) {
      setTimeout(() => this.dismiss(id), duration);
    }
    return id;
  }

  /** Convenience methods - all 5-6 seconds for professional feel */
  success(message: string) { return this.show(message, 'success', 5000); }
  error(message: string) { return this.show(message, 'error', 6000); }
  warning(message: string) { return this.show(message, 'warning', 5500); }
  info(message: string) { return this.show(message, 'info', 5000); }

  dismiss(id: string) {
    this.toasts.update((list) => list.filter((t) => t.id !== id));
  }

  clear() {
    this.toasts.set([]);
  }
}
