import { AfterViewInit, ChangeDetectionStrategy, Component, DestroyRef, ElementRef, OnDestroy, computed, inject, signal, viewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { map, switchMap } from 'rxjs';
import maplibregl from 'maplibre-gl';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ComparisonFlags, HotelCompareData, HotelCompareItem } from '../../models/hotel-compare.model';
import { HotelCompareApiService } from '../../services/hotel-compare-api.service';

/** Map amenity keywords to Material Symbols icons. */
const AMENITY_ICONS: Record<string, string> = {
  wifi: 'wifi',
  'wi-fi': 'wifi',
  internet: 'wifi',
  piscina: 'pool',
  pool: 'pool',
  alberca: 'pool',
  desayuno: 'breakfast_dining',
  breakfast: 'breakfast_dining',
  restaurante: 'restaurant',
  restaurant: 'restaurant',
  gym: 'fitness_center',
  gimnasio: 'fitness_center',
  'estacionamiento': 'local_parking',
  parking: 'local_parking',
  'aire acondicionado': 'ac_unit',
  ac: 'ac_unit',
  'air conditioning': 'ac_unit',
  'tv': 'tv',
  television: 'tv',
  'bar': 'local_bar',
  'spa': 'spa',
  'lavandería': 'local_laundry_service',
  laundry: 'local_laundry_service',
  'transporte': 'airport_shuttle',
  shuttle: 'airport_shuttle',
  'negocios': 'business_center',
  'business center': 'business_center',
  'mascotas': 'pets',
  pets: 'pets',
  'pet': 'pets',
  'vista': 'visibility',
  view: 'visibility',
  'terraza': 'deck',
  terrace: 'deck',
  'jardín': 'grass',
  garden: 'grass',
  'playa': 'beach_access',
  beach: 'beach_access',
  'mar': 'beach_access',
  'montaña': 'terrain',
  mountain: 'terrain',
  'recepción': 'concierge',
  'front desk': 'concierge',
  'seguridad': 'security',
  security: 'security',
  'ascensor': 'elevator',
  elevator: 'elevator',
  'calefacción': 'mode_heat',
  heating: 'mode_heat',
  'cocina': 'kitchen',
  kitchen: 'kitchen',
  'microondas': 'microwave',
  microwave: 'microwave',
  'refrigerador': 'kitchen',
  fridge: 'kitchen',
  'cafetera': 'coffee',
  coffee: 'coffee',
  'agua': 'water_drop',
  water: 'water_drop',
  'toallas': 'bathtub',
  towels: 'bathtub',
  'secador': 'air',
  'hair dryer': 'air',
  'plancha': 'iron',
  iron: 'iron',
  'caja fuerte': 'lock',
  safe: 'lock',
  'teléfono': 'phone_in_talk',
  phone: 'phone_in_talk',
  'adaptador': 'power',
  adapter: 'power',
  'universal': 'power',
  'enchufe': 'power',
  outlet: 'power',
  'escritorio': 'desk',
  desk: 'desk',
  'silla': 'chair',
  chair: 'chair',
  'balcón': 'balcony',
  balcony: 'balcony',
  'hamaca': 'deck',
  'sombrilla': 'umbrella',
  umbrella: 'umbrella',
  'quemador': 'outdoor_grill',
  grill: 'outdoor_grill',
  'fogata': 'local_fire_department',
  fireplace: 'local_fire_department',
};

/** Amenity category definitions with color themes (Expedia/Booking.com style). */
const AMENITY_CATEGORIES: Record<string, { keywords: string[]; color: string; bgColor: string; icon: string; label: string }> = {
  conectividad: {
    keywords: ['wifi', 'wi-fi', 'internet'],
    color: '#1463ff',
    bgColor: 'rgba(20, 99, 255, 0.1)',
    icon: 'wifi',
    label: 'Conectividad'
  },
  piscina: {
    keywords: ['piscina', 'pool', 'alberca'],
    color: '#0d9488',
    bgColor: 'rgba(13, 148, 136, 0.1)',
    icon: 'pool',
    label: 'Piscina'
  },
  comida: {
    keywords: ['desayuno', 'breakfast', 'restaurante', 'restaurant', 'bar', 'cafetera', 'coffee'],
    color: '#d97706',
    bgColor: 'rgba(217, 119, 6, 0.1)',
    icon: 'breakfast_dining',
    label: 'Comida y bebida'
  },
  wellness: {
    keywords: ['spa', 'gym', 'gimnasio', 'fitness', 'sauna', 'masaje', 'bañera', 'hidromasaje', 'jaccuzi'],
    color: '#7c3aed',
    bgColor: 'rgba(124, 58, 237, 0.1)',
    icon: 'spa',
    label: 'Wellness'
  },
  transporte: {
    keywords: ['estacionamiento', 'parking', 'transporte', 'shuttle', 'airport', 'traslado'],
    color: '#059669',
    bgColor: 'rgba(5, 150, 105, 0.1)',
    icon: 'local_parking',
    label: 'Transporte'
  },
  habitacion: {
    keywords: ['aire acondicionado', 'ac', 'air conditioning', 'tv', 'television', 'calefacción', 'heating', 'cocina', 'kitchen', 'microondas', 'refrigerador', 'fridge', 'caja fuerte', 'safe', 'escritorio', 'desk', 'plancha', 'iron', 'secador', 'hair dryer', 'toallas', 'towels', 'agua', 'water', 'cafetera', 'coffee'],
    color: '#1463ff',
    bgColor: 'rgba(20, 99, 255, 0.1)',
    icon: 'ac_unit',
    label: 'En la habitación'
  },
  exterior: {
    keywords: ['vista', 'view', 'terraza', 'terrace', 'balcón', 'balcony', 'jardín', 'garden', 'playa', 'beach', 'mar', 'montaña', 'mountain', 'hamaca', 'sombrilla', 'umbrella', 'quemador', 'grill', 'fogata', 'fireplace'],
    color: '#0f8a60',
    bgColor: 'rgba(15, 138, 96, 0.1)',
    icon: 'deck',
    label: 'Exteriores'
  },
  servicios: {
    keywords: ['recepción', 'front desk', 'concierge', 'seguridad', 'security', 'ascensor', 'elevator', 'lavandería', 'laundry', 'negocios', 'business center', 'mascotas', 'pets', 'pet', 'teléfono', 'phone', 'adaptador', 'adapter', 'universal', 'enchufe', 'outlet', 'caja fuerte', 'safe'],
    color: '#6b7280',
    bgColor: 'rgba(107, 114, 128, 0.1)',
    icon: 'concierge',
    label: 'Servicios'
  },
};

@Component({
  selector: 'app-hotel-compare-page',
  imports: [
    RouterLink,
  ],
  templateUrl: './hotel-compare-page.html',
  styleUrl: './hotel-compare-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HotelComparePageComponent implements OnDestroy, AfterViewInit {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly compareApi = inject(HotelCompareApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly compareData = signal<HotelCompareData | null>(null);
  readonly propIds = signal<number[]>([]);
  readonly expandedRooms = signal<Set<number>>(new Set());
  readonly imageErrors = signal<Set<string>>(new Set());
  /** Current slide index per hotel propId. */
  readonly carouselSlides = signal<Map<number, number>>(new Map());
  /** Map container element. */
  private readonly _mapContainer = viewChild<ElementRef<HTMLElement>>('mapContainer');
  private _map: maplibregl.Map | null = null;
  private _userMarker: maplibregl.Marker | null = null;
  private _hotelMarkers: maplibregl.Marker[] = [];
  readonly userLocation = signal<{ lat: number; lng: number } | null>(null);
  /** Per-hotel flags showing which attributes beat the average. */
  readonly comparisonResults = computed(() => {
    const items = this.compareData()?.items;
    if (!items?.length) return new Map<number, ComparisonFlags>();

    const n = items.length;
    const hasPrice = items.filter((i) => i.minNightlyRate != null);
    const avgPrice = hasPrice.length ? hasPrice.reduce((s, i) => s + i.minNightlyRate!, 0) / hasPrice.length : 0;
    const avgScore = items.reduce((s, i) => s + (i.propReviewScore ?? 0), 0) / n;
    const avgStars = items.reduce((s, i) => s + (i.propStarrating ?? 0), 0) / n;
    const avgRoomTypes = items.reduce((s, i) => s + i.roomTypes.length, 0) / n;

    const map = new Map<number, ComparisonFlags>();
    for (const item of items) {
      map.set(item.propId, {
        betterPrice: item.minNightlyRate != null && item.minNightlyRate < avgPrice,
        betterScore: item.propReviewScore != null && item.propReviewScore > avgScore,
        betterStars: item.propStarrating != null && item.propStarrating > avgStars,
        betterRoomTypes: item.roomTypes.length > avgRoomTypes,
      });
    }
    return map;
  });

  /** Auto-play interval refs per hotel propId. */
  private readonly _carouselTimers = new Map<number, ReturnType<typeof setInterval>>();

  constructor() {
    this.activatedRoute.queryParamMap
      .pipe(
        map((qpm) => {
          const raw = qpm.getAll('prop_id').flatMap((v) => {
            const n = Number(v);
            return !Number.isNaN(n) && n > 0 ? [n] : [];
          });
          return [...new Set(raw)].slice(0, 3);
        }),
        switchMap((ids) => {
          if (!ids.length) {
            this.viewState.set('empty');
            return [];
          }
          this.propIds.set(ids);
          const checkIn = this.activatedRoute.snapshot.queryParamMap.get('check_in') ?? '';
          const checkOut = this.activatedRoute.snapshot.queryParamMap.get('check_out') ?? '';
          const adults = Number(this.activatedRoute.snapshot.queryParamMap.get('adults') ?? '1');
          const children = Number(this.activatedRoute.snapshot.queryParamMap.get('children') ?? '0');
          this.viewState.set('loading');
          return this.compareApi.compare(ids, checkIn, checkOut, adults, children);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (data) => {
          if (!data) return;
          this.compareData.set(data);
          this.viewState.set(data.items.length ? 'success' : 'empty');
          this._placeMarkers();
        },
        error: () => {
          this.viewState.set('error');
        },
      });
  }

  /** ═══ Map lifecycle ═══ */

  ngAfterViewInit() {
    const el = this._mapContainer();
    if (!el) return;

    this._map = new maplibregl.Map({
      container: el.nativeElement,
      style: 'https://tiles.openfreemap.org/styles/liberty',
      center: [-93.0, 23.0],
      zoom: 5,
      attributionControl: false,
    });

    this._map.addControl(new maplibregl.NavigationControl(), 'top-right');
    this._map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-left');

    this._map.on('load', () => this._placeMarkers());
  }

  private _placeMarkers() {
    const data = this.compareData();
    if (!data?.items.length || !this._map) return;

    this._destroyMarkers();

    const bounds = new maplibregl.LngLatBounds();
    const colours = ['#1463FF', '#059669', '#D97706'];

    for (let i = 0; i < data.items.length; i++) {
      const h = data.items[i];
      const colour = colours[i % colours.length];

      // Marker element
      const markerEl = document.createElement('div');
      markerEl.className = 'hotel-marker';
      markerEl.innerHTML = `<span class="material-symbols-outlined" style="font-size:1.5rem;color:${colour}">hotel</span>`;
      markerEl.title = h.hotelName;

      const marker = new maplibregl.Marker({ element: markerEl, anchor: 'bottom' })
        .setLngLat([h.longitude, h.latitude])
        .setPopup(new maplibregl.Popup({ offset: 25 }).setHTML(`
          <div class="map-popup">
            <strong>${h.hotelName}</strong>
            ${h.minNightlyRateLabel ? `<div class="map-popup-price">Desde ${h.minNightlyRateLabel}/noche</div>` : ''}
            ${h.propStarrating ? `<div class="map-popup-stars">${'★'.repeat(Math.round(h.propStarrating))} ${h.propStarrating}</div>` : ''}
            ${h.propReviewScore ? `<div class="map-popup-score">Puntuación: ${h.propReviewScore.toFixed(1)}</div>` : ''}
          </div>
        `))
        .addTo(this._map);

      this._hotelMarkers.push(marker);
      bounds.extend([h.longitude, h.latitude]);
    }

    // Try user location
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = pos.coords.latitude;
          const lng = pos.coords.longitude;
          this.userLocation.set({ lat, lng });
          this._addUserMarker(lat, lng);
          bounds.extend([lng, lat]);
          this._map?.fitBounds(bounds, { padding: 60, maxZoom: 10 });
        },
        () => {
          // geo denied → just fit hotels
          this._map?.fitBounds(bounds, { padding: 60, maxZoom: 10 });
        },
      );
    } else {
      this._map?.fitBounds(bounds, { padding: 60, maxZoom: 10 });
    }
  }

  private _addUserMarker(lat: number, lng: number) {
    if (!this._map) return;
    this._userMarker?.remove();

    const el = document.createElement('div');
    el.className = 'user-marker';
    el.innerHTML = `<span class="material-symbols-outlined" style="font-size:1.4rem;color:#D32F2F">person_pin_circle</span>`;
    el.title = 'Tu ubicación';

    this._userMarker = new maplibregl.Marker({ element: el, anchor: 'bottom' })
      .setLngLat([lng, lat])
      .setPopup(new maplibregl.Popup({ offset: 25 }).setHTML(`<div class="map-popup"><strong>Tu ubicación</strong></div>`))
      .addTo(this._map);
  }

  private _destroyMarkers() {
    for (const m of this._hotelMarkers) m.remove();
    this._hotelMarkers = [];
    this._userMarker?.remove();
    this._userMarker = null;
  }

  /** Fit map to show all hotels (and user location). */
  fitMapToHotels() {
    const data = this.compareData();
    if (!data?.items.length || !this._map) return;
    const bounds = new maplibregl.LngLatBounds();
    for (const h of data.items) {
      bounds.extend([h.longitude, h.latitude]);
    }
    const userLoc = this.userLocation();
    if (userLoc) bounds.extend([userLoc.lng, userLoc.lat]);
    this._map.fitBounds(bounds, { padding: 60, maxZoom: 10 });
  }

  readonly removeId = (id: number) => {
    const remaining = this.propIds().filter((pid) => pid !== id);
    if (!remaining.length) {
      void this.router.navigate(['/search']);
      return;
    }
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { prop_id: remaining },
      queryParamsHandling: 'merge',
    });
  };

  readonly addMoreUrl = computed(() => {
    const existing = this.propIds();
    return `/search` + (existing.length ? `?compare_ids=${existing.join(',')}` : '');
  });

  /** Build the CSS transform for the carousel track. */
  carouselTransform(slide: number): string {
    return `translateX(-${slide * 100}%)`;
  }

  /** Generate carousel image URLs for a hotel using picsum.photos with seed. */
  carouselImages(hotel: HotelCompareItem): string[] {
    const seed = hotel.propId;
    return [
      hotel.imageUrl || `https://picsum.photos/seed/${seed}1/400/250`,
      `https://picsum.photos/seed/${seed}2/400/250`,
      `https://picsum.photos/seed/${seed}3/400/250`,
      `https://picsum.photos/seed/${seed}4/400/250`,
    ];
  }

  /** Get current slide index for a hotel. */
  currentSlide(propId: number): number {
    return this.carouselSlides().get(propId) ?? 0;
  }

  /** Navigate carousel to a specific slide. */
  goToSlide(propId: number, index: number, total: number) {
    const clamped = ((index % total) + total) % total;
    const next = new Map(this.carouselSlides());
    next.set(propId, clamped);
    this.carouselSlides.set(next);
  }

  /** Start auto-play for a hotel. Clears previous timer if any. */
  startAutoPlay(propId: number, total: number) {
    this.stopAutoPlay(propId);
    const timer = setInterval(() => {
      const current = this.carouselSlides().get(propId) ?? 0;
      this.goToSlide(propId, current + 1, total);
    }, 4000);
    this._carouselTimers.set(propId, timer);
  }

  /** Stop auto-play for a hotel. */
  stopAutoPlay(propId: number) {
    const timer = this._carouselTimers.get(propId);
    if (timer) {
      clearInterval(timer);
      this._carouselTimers.delete(propId);
    }
  }

  /** Toggle expand/collapse for a hotel's room types. */
  toggleRooms(propId: number) {
    const current = this.expandedRooms();
    const next = new Set(current);
    if (next.has(propId)) {
      next.delete(propId);
    } else {
      next.add(propId);
    }
    this.expandedRooms.set(next);
  }

  /** Mark a hotel image as errored. Key format: 'propId-index' for carousel slides. */
  handleImageError(key: string) {
    const current = this.imageErrors();
    const next = new Set(current);
    next.add(key);
    this.imageErrors.set(next);
  }

  ngOnDestroy() {
    for (const timer of this._carouselTimers.values()) {
      clearInterval(timer);
    }
    this._carouselTimers.clear();
    this._destroyMarkers();
    this._map?.remove();
    this._map = null;
  }

  /** Look up comparison flags for a hotel. */
  hotelFlags(propId: number): ComparisonFlags | undefined {
    return this.comparisonResults().get(propId);
  }

  /** Map an amenity name to its closest Material Symbols icon. */
  amenityIcon(amenity: string): string {
    const key = amenity.toLowerCase().trim();
    return AMENITY_ICONS[key] || 'check_circle';
  }

  /** Map a policy label to its Material Symbols icon. */
  policyIcon(label: string): string {
    const icons: Record<string, string> = {
      'Check-in': 'login',
      'Check-out': 'logout',
      'Mascotas': 'pets',
      'Niños': 'child_care',
      'Camas extra': 'bed',
      'Pagos': 'payments',
      'Reglas': 'gavel',
    };
    return icons[label] || 'info';
  }

  /** Parse comma-separated amenity text into a clean list. */
  amenityList(text: string | undefined | null): string[] {
    if (!text) return [];
    return text.split(',').map((t) => t.trim()).filter(Boolean);
  }

  /** Categorize amenities by type with color themes (Expedia/Booking.com style). */
  categorizeAmenities(text: string | undefined | null): { category: string; label: string; color: string; bgColor: string; icon: string; amenities: string[] }[] {
    const amenities = this.amenityList(text);
    if (!amenities.length) return [];

    const categorized: Record<string, string[]> = {};
    const uncategorized: string[] = [];

    for (const amenity of amenities) {
      let matched = false;
      for (const [catKey, catDef] of Object.entries(AMENITY_CATEGORIES)) {
        for (const keyword of catDef.keywords) {
          if (amenity.toLowerCase().includes(keyword.toLowerCase())) {
            if (!categorized[catKey]) categorized[catKey] = [];
            categorized[catKey].push(amenity);
            matched = true;
            break;
          }
        }
        if (matched) break;
      }
      if (!matched) {
        uncategorized.push(amenity);
      }
    }

    const result: { category: string; label: string; color: string; bgColor: string; icon: string; amenities: string[] }[] = [];
    for (const [catKey, catDef] of Object.entries(AMENITY_CATEGORIES)) {
      if (categorized[catKey]?.length) {
        result.push({
          category: catKey,
          label: catDef.label,
          color: catDef.color,
          bgColor: catDef.bgColor,
          icon: catDef.icon,
          amenities: categorized[catKey]
        });
      }
    }
    if (uncategorized.length) {
      result.push({
        category: 'otros',
        label: 'Otros',
        color: '#6b7280',
        bgColor: 'rgba(107, 114, 128, 0.1)',
        icon: 'check_circle',
        amenities: uncategorized
      });
    }
    return result;
  }

  /** Get the minimum nightly rate across compared hotels as a display string. */
  minRate(items: HotelCompareItem[]): string {
    if (!items?.length) return '—';
    const item = items.find(i => i.minNightlyRateLabel);
    return item?.minNightlyRateLabel || '—';
  }
}
