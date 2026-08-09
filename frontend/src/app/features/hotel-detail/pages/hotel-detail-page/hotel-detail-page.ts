import { ChangeDetectionStrategy, Component, computed, effect, inject, isDevMode, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DatePipe } from '@angular/common';

import { TrackingService } from '../../../../core/tracking/tracking.service';
import { API_CONFIG } from '../../../../core/api/api.config';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { ImageLightboxComponent } from '../../../../shared/ui/image-lightbox/image-lightbox';
import { SimilarCarouselComponent } from '../../components/similar-carousel/similar-carousel';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { HotelDetailViewModel, SimilarHotel } from '../../models/hotel-detail.model';
import type { HotelDetailDto, SimilarHotelsResponseDto } from '../../models/hotel-detail.dto';
import { HotelDetailApiService, mapSimilarHotel } from '../../services/hotel-detail-api.service';
import { mapHotelDetailResponse } from '../../mappers/hotel-detail.mapper';

@Component({
  selector: 'app-hotel-detail-page',
  imports: [DatePipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, RouterLink, ImageLightboxComponent, SimilarCarouselComponent],
  templateUrl: './hotel-detail-page.html',
  styleUrl: './hotel-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HotelDetailPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly hotelDetailApi = inject(HotelDetailApiService);
  private readonly trackingService = inject(TrackingService);
  private readonly apiConfig = inject(API_CONFIG);

  /**
   * Reactive snapshot of the route's `paramMap`. Initialised from
   * `snapshot.paramMap` so the first httpResource request fires on direct
   * navigation (no flash of `hotelId=0` → loading → real data).
   *
   * `hotelId` below is a single-primitive `computed`; default `Object.is`
   * equality already dedups upstream noise, no `distinctUntilChanged` needed.
   */
  private readonly paramMap = toSignal(this.activatedRoute.paramMap, {
    initialValue: this.activatedRoute.snapshot.paramMap,
  });

  private readonly hotelId = computed(() =>
    Number(this.paramMap().get('hotelId') ?? '0')
  );

  readonly hotelResource = httpResource<HotelDetailViewModel>(() => {
    const id = this.hotelId();
    return id > 0 ? `/api/hotels/${id}` : undefined;
  }, {
    parse: (dto) => mapHotelDetailResponse(dto as HotelDetailDto),
  });

  readonly hotel = computed(() => this.hotelResource.value() ?? null);
  readonly viewState = computed<ViewState>(() => {
    if (this.hotelResource.isLoading()) return 'loading';
    const err = this.hotelResource.error() as { status?: number } | null;
    if (err) return err.status === 404 ? 'empty' : 'error';
    return this.hotel() ? 'success' : 'loading';
  });

  readonly similarHotelsResource = httpResource<SimilarHotel[]>(() => {
    const id = this.hotel()?.id;
    return id ? `/api/hotels/${id}/similar` : undefined;
  }, {
    parse: (dto) => (dto as SimilarHotelsResponseDto).items.map(mapSimilarHotel),
  });
  readonly similarHotels = computed(() => this.similarHotelsResource.value() ?? []);
  readonly similarLoading = computed(() => this.similarHotelsResource.isLoading());

  readonly activeTab = signal<string>('overview');
  readonly imageErrors = signal<Set<string>>(new Set());
  readonly selectedGalleryImage = signal<string | null>(null);
  readonly lightboxOpen = signal(false);
  readonly showSimilarInfo = signal(false);
  readonly showBooking = signal(false);

  onImageError(key: string, event?: Event) {
    this.imageErrors.update((s) => new Set(s).add(key));
    // Dev visibility: log the failing URL + the gallery key so devs can
    // tell whether the failure came from a real hotel_images entry or
    // from the loremflickr placeholder fallback. Browser DevTools logs
    // HTTP 404s as Network-tab entries (not Console), so without this
    // explicit console.error the broken images are invisible while
    // rendering the placeholder icon.
    if (event?.target instanceof HTMLImageElement) {
      const src = event.target.src;
      if (isDevMode()) console.error(`[hotel-detail] image load failed · ${key} · ${src}`);
    }
  }

  openGalleryModal(url: string) {
    this.selectedGalleryImage.set(url);
    this.lightboxOpen.set(true);
  }

  closeGalleryModal() {
    this.lightboxOpen.set(false);
  }

  onLightboxClosed(): void {
    this.lightboxOpen.set(false);
    this.selectedGalleryImage.set(null);
  }

  readonly stars = computed(() => {
    const h = this.hotel();
    if (!h) return 0;
    const v = parseInt(h.starsLabel, 10);
    return isNaN(v) ? 0 : v;
  });

  constructor() {
    effect(() => {
      const hotel = this.hotel();
      if (hotel) {
        this.trackingService.trackHotelClick(hotel.id, 'detail');
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
    // Return '' when no Google Maps API key is configured so the iframe
    // doesn't render broken (referer-rejected). Set the key via ApiConfig
    // factory override (provideApiConfig({googleMapsApiKey: '...'}) in
    // app.config.ts) or env-injected token to enable the map.
    const key = this.apiConfig.googleMapsApiKey;
    if (!key) {
      if (isDevMode()) console.warn('[hotel-detail] map disabled — provide API_CONFIG.googleMapsApiKey to /api/hostels/<id> map iframe');
      return '';
    }
    return `https://www.google.com/maps/embed/v1/view?key=${key}&center=${vm.latitude},${vm.longitude}&zoom=14&language=es`;
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

}
