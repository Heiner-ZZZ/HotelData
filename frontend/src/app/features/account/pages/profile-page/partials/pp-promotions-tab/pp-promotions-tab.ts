import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { Router } from '@angular/router';

import { EmptyStateComponent } from '../../../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../../../shared/ui/loading-state/loading-state';
import { ClientNotificationsService } from '../../../../../notifications/services/notifications.service';
import { mapMyNotifications } from '../../../../../notifications/mappers/notifications.mapper';
import type { MyNotificationsDto } from '../../../../../notifications/models/notifications.dto';
import type { ClientNotification, MyNotifications } from '../../../../../notifications/models/notifications.model';

/** Tipo promocional en notification_log (envíos de publicidad/promociones). */
const PROMOTIONAL_TYPE = 'guest_promotional';
/** Promociones por página (el backend filtra por tipo; ya no trae transaccionales). */
const PAGE_SIZE = 10;

@Component({
  selector: 'app-pp-promotions-tab',
  imports: [DatePipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent],
  templateUrl: './pp-promotions-tab.html',
  styleUrl: './pp-promotions-tab.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PpPromotionsTabComponent {
  private readonly notificationsService = inject(ClientNotificationsService);
  private readonly router = inject(Router);

  /** Página actual de promocionales (solo guest_promotional, paginado en el backend). */
  private readonly page = signal(1);

  readonly notificationsResource = httpResource<MyNotifications>(
    () =>
      `/api/notifications/my?notification_type=${PROMOTIONAL_TYPE}&page=${this.page()}&page_size=${PAGE_SIZE}`,
    {
      parse: (dto) => mapMyNotifications(dto as MyNotificationsDto),
    },
  );

  /** Promociones acumuladas de todas las páginas cargadas. */
  readonly items = signal<ClientNotification[]>([]);

  /** Total de promociones que tiene el huésped (viene del backend, filtrado por tipo). */
  readonly total = computed(() => this.notificationsResource.value()?.total ?? 0);

  /** Última página ya acumulada (para no duplicar al re-emitir el recurso). */
  private lastLoadedPage = 0;

  readonly hasMore = computed(() => this.items().length < this.total());
  readonly loadingMore = computed(
    () => this.notificationsResource.isLoading() && this.items().length > 0,
  );

  readonly viewState = computed<'loading' | 'error' | 'empty' | 'success'>(() => {
    if (this.items().length === 0 && this.notificationsResource.isLoading()) return 'loading';
    if (this.notificationsResource.error()) return 'error';
    return this.items().length ? 'success' : 'empty';
  });

  constructor() {
    // Acumula cada página en cuanto llega; solo avanza si la página es nueva.
    effect(() => {
      const data = this.notificationsResource.value();
      if (!data || data.page <= this.lastLoadedPage) return;
      this.lastLoadedPage = data.page;
      this.items.update((prev) => [...prev, ...data.items]);
    });
  }

  loadMore(): void {
    if (this.hasMore() && !this.loadingMore()) {
      this.page.update((p) => p + 1);
    }
  }

  /** Marca la promoción como leída (dot desaparece) si aún está sin leer. */
  markAsRead(item: ClientNotification): void {
    if (!item.isUnread || !item.id) return;
    this.notificationsService.markAsRead(item.id).subscribe({
      next: () => {
        this.items.update((prev) =>
          prev.map((it) => (it.id === item.id ? { ...it, isUnread: false } : it)),
        );
      },
      // Error silencioso: si falla el marcado, el dot persiste y se puede reintentar.
      error: () => undefined,
    });
  }

  /** Deep link Fase 1: clic en la promo → página pública del hotel.
   *  Navega a ``/hotels/{prop_id}`` y, en paralelo, marca como leída
   *  (el dot de la pestaña y la campanita desaparecen al volver). */
  open(item: ClientNotification): void {
    if (item.propId > 0) {
      void this.router.navigate(['/hotels', item.propId]);
    }
    this.markAsRead(item);
  }
}
