import { CurrencyPipe, AsyncPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { map, switchMap } from 'rxjs';

import { ReservationsApiService } from '../../services/reservations-api.service';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';

@Component({
  selector: 'app-booking-confirmed-page',
  imports: [CurrencyPipe, AsyncPipe, LoadingStateComponent, RouterLink],
  templateUrl: './booking-confirmed-page.html',
  styleUrl: './booking-confirmed-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BookingConfirmedPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly reservationsApi = inject(ReservationsApiService);

  readonly booking$ = this.activatedRoute.paramMap.pipe(
    map((params) => params.get('bookingId') ?? ''),
    switchMap((id) => this.reservationsApi.getReservationDetail(id)),
  );

  copyRef(text: string) {
    navigator.clipboard.writeText(text).catch(() => {});
  }
}
