import { ChangeDetectionStrategy, Component, computed, effect, inject, isDevMode, signal } from '@angular/core';
import { HttpClient, httpResource } from '@angular/common/http';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DatePipe } from '@angular/common';

import { TrackingService } from '../../../../core/tracking/tracking.service';
import { API_CONFIG } from '../../../../core/api/api.config';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { ImageLightboxComponent } from '../../../../shared/ui/image-lightbox/image-lightbox';
import { CarouselControlsComponent } from '../../../../shared/ui/carousel-controls/carousel-controls';
import { SimilarCarouselComponent } from '../../components/similar-carousel/similar-carousel';
import { HotelOffersComponent } from '../../components/hotel-offers/hotel-offers';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { HotelDetailViewModel, SimilarHotel } from '../../models/hotel-detail.model';
import type { HotelDetailDto, RoomAvailabilitySnapshotDto, SimilarHotelsResponseDto } from '../../models/hotel-detail.dto';
import { HotelDetailApiService, mapSimilarHotel } from '../../services/hotel-detail-api.service';
import { mapHotelDetailResponse } from '../../mappers/hotel-detail.mapper';

@Component({
  selector: 'app-hotel-detail-page',
  imports: [DatePipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, RouterLink, ImageLightboxComponent, CarouselControlsComponent, SimilarCarouselComponent, HotelOffersComponent],
  templateUrl: './hotel-detail-page.html',
  styleUrl: './hotel-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HotelDetailPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);

  /** Dates inherited from the search page URL (check_in/check_out query params).
   *  Passed through to the "Reservar Ahora" links so guests don't lose their
   *  search dates when navigating to the booking form. */
  readonly inheritedCheckIn = signal(this.activatedRoute.snapshot.queryParamMap.get('check_in') ?? '');
  readonly inheritedCheckOut = signal(this.activatedRoute.snapshot.queryParamMap.get('check_out') ?? '');
  private readonly hotelDetailApi = inject(HotelDetailApiService);
  private readonly trackingService = inject(TrackingService);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly http = inject(HttpClient);

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

  // ── Snapshot próximos 7 días por habitación (consulta sin adivinar fechas) ──
  readonly roomAvailabilityResource = httpResource<RoomAvailabilitySnapshotDto>(() => {
    const id = this.hotelId();
    return id > 0 ? `/api/hotels/${id}/availability/snapshot?days=7` : undefined;
  });
  readonly roomAvailabilitySnapshot = computed(() => this.roomAvailabilityResource.value() ?? null);
  readonly roomAvailabilityLoading = computed(() => this.roomAvailabilityResource.isLoading());

  readonly activeTab = signal<string>('overview');
  readonly imageErrors = signal<Set<string>>(new Set());
  readonly selectedGalleryImage = signal<string | null>(null);
  readonly lightboxOpen = signal(false);
  readonly showSimilarInfo = signal(false);
  readonly showBooking = signal(false);

  // ── Carrusel de fotos por habitación (puntitos tipo comparador) ──

  /** Slide activo por tipo de habitación (keyed por room_type_id). */
  readonly roomSlides = signal<Record<string, number>>({});

  /** Índice activo de la galería de la habitación (0 si nunca se tocó). */
  roomSlide(roomId: string): number {
    return this.roomSlides()[roomId] ?? 0;
  }

  /** Offset translateX del track de la galería de la habitación. */
  roomOffset(roomId: string, slide: number): string {
    return `translateX(-${slide * 100}%)`;
  }

  /** Cambia el slide de la habitación (sin propagar clics del card). */
  roomGoTo(roomId: string, idx: number): void {
    this.roomSlides.update((m) => ({ ...m, [roomId]: idx }));
  }

  /** Flechas prev/next de la habitación: navegan con wrap-around. */
  roomStep(roomId: string, dir: 1 | -1): void {
    const total = this.roomSlidesCount(roomId);
    if (total <= 1) return;
    const current = this.roomSlide(roomId);
    this.roomGoTo(roomId, (current + dir + total) % total);
  }

  private roomSlidesCount(roomId: string): number {
    return this.hotel()?.roomTypes.find((rt) => rt.id === roomId)?.images.length ?? 0;
  }

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

  // ── Helpers para snapshot por habitación ──
  roomAvailabilityFor(roomId: string) {
    return this.roomAvailabilitySnapshot()?.rooms.find((r) => r.room_type_id === roomId) ?? null;
  }

  roomNextPrice(roomId: string): string | null {
    const room = this.roomAvailabilityFor(roomId);
    if (!room) return null;
    const available = room.availability.filter((d) => d.is_available && d.min_rate !== null);
    if (!available.length) return null;
    const min = Math.min(...available.map((d) => d.min_rate as number));
    return `$${min.toFixed(2)}`;
  }

  roomNextAvailableCount(roomId: string): number {
    const room = this.roomAvailabilityFor(roomId);
    return room ? room.availability.filter((d) => d.is_available).length : 0;
  }

  formatDayLabel(dateStr: string): string {
    try {
      const d = new Date(dateStr + 'T00:00:00');
      const weekdays = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
      const day = d.getDate();
      const wd = weekdays[d.getDay()];
      return `${wd} ${day}`;
    } catch {
      return dateStr;
    }
  }

  // ── Selección multi-día por habitación (TDD) ──
  readonly selectedRanges = signal<Record<string, { start: string; end: string }>>({});

  isDaySelected(roomId: string, dateStr: string): boolean {
    const sel = this.selectedRanges()[roomId];
    if (!sel) return false;
    return dateStr === sel.start || dateStr === sel.end.replace(/-(\d+)$/, (_, d) => {
      // end es exclusivo, no se pinta como seleccionado (es checkout)
      return '';
    }) || false;
    // End es exclusivo: solo start es seleccionado, end no se muestra. Para rango 25→27, start=25 end=27, días 25,26 seleccionados.
  }

  isDayInRange(roomId: string, dateStr: string): boolean {
    const sel = this.selectedRanges()[roomId];
    if (!sel) return false;
    // end es exclusivo, rango [start, end)
    return dateStr >= sel.start && dateStr < sel.end;
  }

  isDayRangeStart(roomId: string, dateStr: string): boolean {
    const sel = this.selectedRanges()[roomId];
    return !!sel && dateStr === sel.start;
  }

  isDayRangeEnd(roomId: string, dateStr: string): boolean {
    const sel = this.selectedRanges()[roomId];
    if (!sel) return false;
    // end es checkout, no es noche; la última noche es end-1
    const endLastNight = new Date(sel.end + 'T00:00:00');
    endLastNight.setDate(endLastNight.getDate() - 1);
    return dateStr === endLastNight.toISOString().slice(0, 10);
  }

  selectedNights(roomId: string): number | null {
    const sel = this.selectedRanges()[roomId];
    if (!sel) return null;
    const start = new Date(sel.start + 'T00:00:00');
    const end = new Date(sel.end + 'T00:00:00');
    const diff = Math.round((end.getTime() - start.getTime()) / 86_400_000);
    return diff >= 1 ? diff : null;
  }

  selectedTotal(roomId: string): string | null {
    const sel = this.selectedRanges()[roomId];
    const room = this.roomAvailabilityFor(roomId);
    if (!sel || !room) return null;
    const nights = this.selectedNights(roomId);
    if (!nights) return null;
    // Suma de min_rate por noche en el rango seleccionado
    let total = 0;
    const start = new Date(sel.start + 'T00:00:00');
    const end = new Date(sel.end + 'T00:00:00');
    for (let d = new Date(start); d < end; d.setDate(d.getDate() + 1)) {
      const ds = d.toISOString().slice(0, 10);
      const day = room.availability.find((a) => a.date === ds);
      if (!day || !day.is_available || day.min_rate === null) return null;
      total += day.min_rate;
    }
    return `$${total.toFixed(2)}`;
  }

  roomReserveQuery(roomId: string, roomName: string) {
    const sel = this.selectedRanges()[roomId];
    if (sel) {
      return { prop_id: this.hotel()?.id, room_type: roomId, room_type_name: roomName, check_in: sel.start, check_out: sel.end };
    }
    return { prop_id: this.hotel()?.id, room_type: roomId, room_type_name: roomName, check_in: this.inheritedCheckIn() || null, check_out: this.inheritedCheckOut() || null };
  }

  private persistSelectedDates(start: string, end: string): void {
    try {
      localStorage.setItem('hoteldata.selected_check_in', start);
      localStorage.setItem('hoteldata.selected_check_out', end);
      if (this.hotel()?.id) {
        localStorage.setItem(`hoteldata.hotel_${this.hotel()!.id}_check_in`, start);
        localStorage.setItem(`hoteldata.hotel_${this.hotel()!.id}_check_out`, end);
      }
    } catch {}
    // Redis via session-prefs (mismo que search)
    this.http.put('/api/guest/session-prefs', { check_in: start, check_out: end }).subscribe({
      error: () => {},
    });
  }

  selectAvailabilityDay(roomId: string, day: import('../../models/hotel-detail.dto').RoomAvailabilityDayDto): void {
    if (!day.is_available) return;
    const clicked = day.date;
    const current = this.selectedRanges()[roomId];
    const room = this.roomAvailabilityFor(roomId);

    if (!current) {
      // Primer clic: una noche
      const out = new Date(clicked + 'T00:00:00');
      out.setDate(out.getDate() + 1);
      const end = out.toISOString().slice(0, 10);
      this.selectedRanges.update((m) => ({ ...m, [roomId]: { start: clicked, end } }));
      this.inheritedCheckIn.set(clicked);
      this.inheritedCheckOut.set(end);
      this.persistSelectedDates(clicked, end);
      return;
    }

    const start = current.start;
    const end = current.end;

    // Clic en el mismo inicio: limpia
    if (clicked === start && this.selectedNights(roomId) === 1) {
      const next = { ...this.selectedRanges() };
      delete next[roomId];
      this.selectedRanges.set(next);
      this.inheritedCheckIn.set('');
      this.inheritedCheckOut.set('');
      try {
        localStorage.removeItem('hoteldata.selected_check_in');
        localStorage.removeItem('hoteldata.selected_check_out');
      } catch {}
      return;
    }

    // Si clickea antes del inicio: nuevo inicio de una noche
    if (clicked < start) {
      const out = new Date(clicked + 'T00:00:00');
      out.setDate(out.getDate() + 1);
      const newEnd = out.toISOString().slice(0, 10);
      this.selectedRanges.update((m) => ({ ...m, [roomId]: { start: clicked, end: newEnd } }));
      this.inheritedCheckIn.set(clicked);
      this.inheritedCheckOut.set(newEnd);
      this.persistSelectedDates(clicked, newEnd);
      return;
    }

    // Clickea después del inicio: extiende rango hasta clicked inclusive
    // Verificar que todo el rango start→clicked sea disponible
    if (room) {
      const s = new Date(start + 'T00:00:00');
      const e = new Date(clicked + 'T00:00:00');
      let allAvailable = true;
      for (let d = new Date(s); d <= e; d.setDate(d.getDate() + 1)) {
        const ds = d.toISOString().slice(0, 10);
        const info = room.availability.find((a) => a.date === ds);
        if (!info || !info.is_available) { allAvailable = false; break; }
      }
      if (!allAvailable) {
        // si hay hueco no disponible, reinicia a una noche en clicked
        const out = new Date(clicked + 'T00:00:00');
        out.setDate(out.getDate() + 1);
        const newEnd = out.toISOString().slice(0, 10);
        this.selectedRanges.update((m) => ({ ...m, [roomId]: { start: clicked, end: newEnd } }));
        this.inheritedCheckIn.set(clicked);
        this.inheritedCheckOut.set(newEnd);
        this.persistSelectedDates(clicked, newEnd);
        return;
      }
    }
    const out = new Date(clicked + 'T00:00:00');
    out.setDate(out.getDate() + 1);
    const newEnd = out.toISOString().slice(0, 10);
    this.selectedRanges.update((m) => ({ ...m, [roomId]: { start, end: newEnd } }));
    this.inheritedCheckIn.set(start);
    this.inheritedCheckOut.set(newEnd);
    this.persistSelectedDates(start, newEnd);
  }

  constructor() {
    effect(() => {
      const hotel = this.hotel();
      if (hotel) {
        this.trackingService.trackHotelClick(hotel.id, 'detail');
      }
    });

    // Si entra con ?check_in/out (desde /search), precarga el rango en cada habitación disponible y persiste
    effect(() => {
      const checkIn = this.inheritedCheckIn();
      const checkOut = this.inheritedCheckOut();
      const snap = this.roomAvailabilitySnapshot();
      if (!checkIn || !checkOut || !snap) return;
      // Evita re-setear si ya hay selección
      if (Object.keys(this.selectedRanges()).length > 0) return;
      const start = new Date(checkIn + 'T00:00:00');
      const end = new Date(checkOut + 'T00:00:00');
      if (isNaN(start.getTime()) || isNaN(end.getTime()) || end <= start) return;
      const newRanges: Record<string, { start: string; end: string }> = {};
      for (const room of snap.rooms) {
        let allAvailable = true;
        for (let d = new Date(start); d < end; d.setDate(d.getDate() + 1)) {
          const ds = d.toISOString().slice(0, 10);
          const day = room.availability.find((a) => a.date === ds);
          if (!day || !day.is_available) { allAvailable = false; break; }
        }
        if (allAvailable) {
          newRanges[room.room_type_id] = { start: checkIn, end: checkOut };
        }
      }
      if (Object.keys(newRanges).length) {
        this.selectedRanges.set(newRanges);
        this.persistSelectedDates(checkIn, checkOut);
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
