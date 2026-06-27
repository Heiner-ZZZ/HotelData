import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { TrackingService } from '../../../../core/tracking/tracking.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { HotelDetailViewModel, SimilarHotel } from '../../models/hotel-detail.model';
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
  private readonly trackingService = inject(TrackingService);

  readonly viewState = signal<ViewState>('loading');
  readonly hotel = signal<HotelDetailViewModel | null>(null);
  readonly activeTab = signal<string>('overview');
  readonly similarHotels = signal<SimilarHotel[]>([]);
  readonly similarLoading = signal(false);
  readonly imageErrors = signal<Set<string>>(new Set());

  onImageError(key: string) {
    this.imageErrors.update((s) => new Set(s).add(key));
  }

  readonly stars = computed(() => {
    const h = this.hotel();
    if (!h) return 0;
    const v = parseInt(h.starsLabel, 10);
    return isNaN(v) ? 0 : v;
  });

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
          this.trackingService.trackHotelClick(hotel.id, 'detail');
          this.loadSimilarHotels(hotel.id);
        },
        error: (error: ApiError) => {
          this.viewState.set(error.status === 404 ? 'empty' : 'error');
        }
      });
  }

  readonly shareHotel = () => {
    const vm = this.hotel();
    if (!vm) return;
    const url = window.location.href;
    const title = vm.name;
    if (typeof navigator.share === 'function') {
      void navigator.share({ title, url });
    } else {
      void navigator.clipboard.writeText(url);
    }
  };

  scrollTo(sectionId: string): void {
    this.activeTab.set(sectionId);
    const el = document.getElementById(sectionId);
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  private loadSimilarHotels(hotelId: number): void {
    this.similarLoading.set(true);
    this.hotelDetailApi.getSimilarHotels(hotelId).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (items) => {
        this.similarHotels.set(items);
        this.similarLoading.set(false);
      },
      error: () => this.similarLoading.set(false),
    });
  }
}
