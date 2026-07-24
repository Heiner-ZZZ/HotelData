import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DatePipe } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { ClientNotificationsService } from '../../services/notifications.service';
import type { MyNotifications } from '../../models/notifications.model';

@Component({
  selector: 'app-notifications-page',
  imports: [RouterLink, DatePipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent],
  templateUrl: './notifications-page.html',
  styleUrl: './notifications-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NotificationsPageComponent {
  private readonly notificationsService = inject(ClientNotificationsService);
  private readonly destroyRef = inject(DestroyRef);

  readonly viewState = signal<'loading' | 'success' | 'error' | 'empty'>('loading');
  readonly data = signal<MyNotifications | null>(null);
  readonly currentPage = signal(1);

  constructor() {
    this.loadPage(1);
  }

  loadPage(page: number): void {
    this.viewState.set('loading');
    this.currentPage.set(page);
    this.notificationsService.getMyNotifications(page, 20).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (result) => {
        this.data.set(result);
        this.viewState.set(result.items.length > 0 ? 'success' : 'empty');
      },
      error: () => this.viewState.set('error'),
    });
  }

  goToPage(page: number): void {
    if (page < 1) return;
    this.loadPage(page);
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
}
