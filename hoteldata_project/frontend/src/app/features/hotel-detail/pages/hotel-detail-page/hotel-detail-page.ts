import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { HotelDetailViewModel } from '../../models/hotel-detail.model';
import { HotelDetailApiService } from '../../services/hotel-detail-api.service';

@Component({
  selector: 'app-hotel-detail-page',
  imports: [EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, RouterLink],
  templateUrl: './hotel-detail-page.html',
  styleUrl: './hotel-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HotelDetailPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly hotelDetailApi = inject(HotelDetailApiService);

  readonly viewState = signal<ViewState>('loading');
  readonly hotel = signal<HotelDetailViewModel | null>(null);

  constructor() {
    this.activatedRoute.paramMap
      .pipe(
        map((params) => Number(params.get('hotelId') ?? '0')),
        distinctUntilChanged(),
        switchMap((hotelId) => {
          this.viewState.set('loading');
          return this.hotelDetailApi.getHotelDetail(hotelId);
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (hotel) => {
          this.hotel.set(hotel);
          this.viewState.set('success');
        },
        error: (error: ApiError) => {
          this.viewState.set(error.status === 404 ? 'empty' : 'error');
        }
      });
  }
}
