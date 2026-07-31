import { CurrencyPipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { mapReservationDetail } from '../../mappers/reservations.mapper';
import type { ReservationDetailDto } from '../../models/reservations.dto';
import type { ReservationDetailViewModel } from '../../models/reservations.model';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';

@Component({
  selector: 'app-booking-confirmed-page',
  imports: [CurrencyPipe, LoadingStateComponent, RouterLink],
  templateUrl: './booking-confirmed-page.html',
  styleUrl: './booking-confirmed-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BookingConfirmedPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);

  /**
   * Reactive snapshot of the route's `paramMap`. Initialized synchronously from
   * `snapshot.paramMap` so the first httpResource fetch kicks off on direct
   * navigation (no flash of empty URL → loading → real data).
   */
  private readonly paramMap = toSignal(this.activatedRoute.paramMap, {
    initialValue: this.activatedRoute.snapshot.paramMap,
  });

  readonly bookingId = computed(() => this.paramMap().get('bookingId') ?? '');

  /**
   * Booking detail view-model. httpResource fetches `/reservations/{id}` and
   * the `parse` callback applies the same snake_case → camel_case mapper that
   * the legacy `ReservationsApiService.getReservationDetail` did internally.
   *
   * In Angular 22 `HttpResourceRef<T>` is not callable — read it via `.value()`
   * (returns `T | undefined`, undefined while loading + before first emit).
   * The template uses `@if (booking.value(); as vm)` so truthiness-narrowing
   * falls through to the loading state when the resource is not yet resolved.
   *
   * T is explicitly declared `<ReservationDetailViewModel>`; the `dto as ReservationDetailDto`
   * cast inside `parse` is the canonical pattern (see `reservation-detail-page.ts:85`).
   */
  readonly booking = httpResource<ReservationDetailViewModel>(() => {
    const id = this.bookingId();
    if (!id) return undefined;
    return `/reservations/${id}`;
  }, {
    parse: (dto) => mapReservationDetail(dto as ReservationDetailDto),
  });

  copyRef(text: string) {
    navigator.clipboard.writeText(text).catch(() => {});
  }
}
