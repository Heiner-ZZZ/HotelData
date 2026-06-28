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

  /** Show a toast notification. Auto-dismisses after `duration` ms (default 5500). */
  show(message: string, type: ToastType = 'info', duration = 5500): string {
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
