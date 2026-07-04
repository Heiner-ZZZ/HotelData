import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { ClientNotificationsService } from '../../services/notifications.service';
import type { ClientNotification } from '../../models/notifications.model';

@Component({
  selector: 'app-notification-bell',
  imports: [RouterLink],
  templateUrl: './notification-bell.html',
  styleUrl: './notification-bell.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NotificationBellComponent {
  private readonly notificationsService = inject(ClientNotificationsService);
  private readonly destroyRef = inject(DestroyRef);

  readonly open = signal(false);
  readonly notifications = signal<ClientNotification[]>([]);
  readonly unreadCount = signal(0);
  readonly loading = signal(false);

  constructor() {
    this.loadNotifications();
  }

  loadNotifications(): void {
    this.loading.set(true);
    this.notificationsService.getMyNotifications(1, 5).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (result) => {
        this.notifications.set(result.items);
        this.unreadCount.set(result.unreadCount);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  toggle(): void {
    this.open.update(v => !v);
    if (this.open()) {
      this.loadNotifications();
    }
  }

  close(): void {
    this.open.set(false);
  }

  notificationIcon(type: string): string {
    if (type.includes('confirmed')) return 'check_circle';
    if (type.includes('rejected') || type.includes('cancelled')) return 'cancel';
    if (type.includes('checked_in')) return 'login';
    if (type.includes('checked_out')) return 'logout';
    if (type.includes('invoice')) return 'receipt_long';
    if (type.includes('amenity')) return 'spa';
    if (type.includes('review')) return 'star';
    return 'notifications';
  }

  iconColor(tone: string): string {
    const colors: Record<string, string> = {
      success: 'var(--success, #16a34a)',
      warning: 'var(--warning, #d97706)',
      danger: 'var(--danger, #e53935)',
    };
    return colors[tone] || 'var(--accent)';
  }

  relativeDate(iso: string): string {
    if (!iso) return '';
    const d = new Date(iso);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Ahora';
    if (mins < 60) return `Hace ${mins} min`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `Hace ${hours} h`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `Hace ${days} d`;
    return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'short' });
  }
}
