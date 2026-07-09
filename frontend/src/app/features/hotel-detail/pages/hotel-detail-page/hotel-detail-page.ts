import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { TrackingService } from '../../../../core/tracking/tracking.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { HotelDetailViewModel, SimilarHotel } from '../../models/hotel-detail.model';
import { HotelDetailApiService } from '../../services/hotel-detail-api.service';

@Component({
  selector: 'app-hotel-detail-page',
  imports: [DatePipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, RouterLink],
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
  readonly selectedGalleryImage = signal<string | null>(null);
  readonly showBooking = signal(false);

  onImageError(key: string) {
    this.imageErrors.update((s) => new Set(s).add(key));
  }

  openGalleryModal(url: string) {
    this.selectedGalleryImage.set(url);
  }

  closeGalleryModal() {
    this.selectedGalleryImage.set(null);
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

  readonly mapUrl = computed(() => {
    const vm = this.hotel();
    if (!vm || !vm.latitude || !vm.longitude) return '';
    return `https://www.google.com/maps/embed/v1/view?key=&center=${vm.latitude},${vm.longitude}&zoom=14&language=es`;
  });

  amenityIcon(amenity: string): string {
    const iconMap: Record<string, string> = {
      wifi: 'wifi', internet: 'wifi', parking: 'local_parking', piscina: 'pool',
      gimnasio: 'fitness_center', restaurante: 'restaurant', spa: 'spa',
      desayuno: 'free_breakfast', aire: 'ac_unit', calefaccion: 'thermostat',
      mascotas: 'pets', transporte: 'directions_car', lavanderia: 'local_laundry_service',
      negocio: 'business_center', sala: 'meeting_room', eventos: 'celebration',
      playa: 'beach_access', tour: 'explore', bar: 'local_bar',
      tv: 'tv', minibar: 'liquor', caja: 'safe',
      terraza: 'deck', jardin: 'yard', vistas: 'panorama',
      'acceso silla': 'accessible', habitaciones: 'meeting_room',
      recepcion: 'concierge', 'servicio hab': 'room_service',
    };
    const key = amenity.toLowerCase().trim();
    return iconMap[key] || iconMap[Object.keys(iconMap).find(k => key.includes(k)) || ''] || 'stars';
  }

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
