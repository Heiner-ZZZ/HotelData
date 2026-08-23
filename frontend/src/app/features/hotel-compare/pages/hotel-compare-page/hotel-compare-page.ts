import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CompareMapComponent } from './components/compare-map';
import { CarouselControlsComponent } from '../../../../shared/ui/carousel-controls/carousel-controls';
import { amenityIcon, carouselImages, categorizeAmenities, computeComparisonFlags, minRate, policyIcon } from './hotel-compare.helpers';
import { getErrorStatus } from '../../../../shared/utils/http-error.util';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ComparisonFlags, HotelCompareData } from '../../models/hotel-compare.model';
import { mapHotelCompareResponse } from '../../mappers/hotel-compare.mapper';
import type { HotelCompareDto } from '../../models/hotel-compare.dto';

@Component({
  selector: 'app-hotel-compare-page',
  imports: [RouterLink, CompareMapComponent, CarouselControlsComponent],
  templateUrl: './hotel-compare-page.html',
  styleUrl: './hotel-compare-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HotelComparePageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);

  /** Reactive queryParams bridge — toSignal keeps URL the source of truth. */
  private readonly qp = toSignal(this.activatedRoute.queryParamMap, {
    initialValue: this.activatedRoute.snapshot.queryParamMap,
  });

  /** Multi-prop_id aggregation parameter — distinct + max 3. */
  private readonly propIdsParam = computed(() => {
    const raw = this.qp().getAll('prop_id').flatMap((v) => {
      const n = Number(v);
      return !Number.isNaN(n) && n > 0 ? [n] : [];
    });
    return [...new Set(raw)].slice(0, 3);
  });

  readonly viewState = computed<ViewState>(() => {
    const ids = this.propIdsParam();
    if (!ids.length) return 'empty';
    // error() ANTES de value(): value() lanza cuando el request falló.
    const err = this.compareResource.error();
    if (err) return getErrorStatus(err) === 404 ? 'empty' : 'error';
    const v = this.compareResource.value();
    if (this.compareResource.isLoading() && !v) return 'loading';
    return v?.items.length ? 'success' : 'empty';
  });

  readonly compareData = computed(() => {
    if (this.compareResource.error()) return null;
    const dto = this.compareResource.value();
    return dto ? mapHotelCompareResponse(dto) : null;
  });
  readonly propIds = computed(() => this.propIdsParam());
  readonly expandedRooms = signal<Set<number>>(new Set());
  readonly imageErrors = signal<Set<string>>(new Set());
  readonly carouselSlides = signal<Map<number, number>>(new Map());
  private readonly _carouselTimers = new Map<number, ReturnType<typeof setInterval>>();

  /** httpResource — auto-fetches whenever URL params change. */
  readonly compareResource = httpResource<HotelCompareDto>(() => {
    const ids = this.propIdsParam();
    if (!ids.length) return undefined;
    const checkIn = this.qp().get('check_in') ?? '';
    const checkOut = this.qp().get('check_out') ?? '';
    const adults = Number(this.qp().get('adults') ?? '1');
    const children = Number(this.qp().get('children') ?? '0');
    const params = new URLSearchParams();
    if (checkIn) params.set('check_in', checkIn);
    if (checkOut) params.set('check_out', checkOut);
    if (adults) params.set('adults', String(adults));
    if (children) params.set('children', String(children));
    // FastAPI declares `prop_id` as a repeated query parameter. Do not use
    // the legacy `/hostels` prefix or a comma-separated `ids` parameter:
    // both produce a 404/empty comparison request.
    for (const id of ids) {
      params.append('prop_id', String(id));
    }
    const qs = params.toString();
    return `/api/hotels/compare?${qs}`;
  });

  readonly comparisonResults = computed(() => {
    const items = this.compareData()?.items;
    return items ? computeComparisonFlags(items) : new Map<number, ComparisonFlags>();
  });

  readonly minRateValue = computed(() => {
    const items = this.compareData()?.items;
    return items ? minRate(items) : '—';
  });

  constructor() {
    // Carousel auto-play timers are torn down here instead of via
    // ``ngOnDestroy``. ``DestroyRef.onDestroy`` runs during the same
    // destruction phase so the lifecycle ordering is equivalent.
    this.destroyRef.onDestroy(() => {
      for (const timer of this._carouselTimers.values()) {
        clearInterval(timer);
      }
      this._carouselTimers.clear();
    });
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
    const params = new URLSearchParams();
    if (existing.length) {
      params.set('compare_ids', existing.join(','));
    }
    const snapshot = this.activatedRoute.snapshot.queryParamMap;
    for (const key of ['check_in', 'check_out']) {
      const val = snapshot.get(key);
      if (val) params.set(key, val);
    }
    for (const key of ['adults', 'children']) {
      const val = snapshot.get(key);
      if (val && val !== (key === 'adults' ? '1' : '0')) params.set(key, val);
    }
    const qs = params.toString();
    return `/search${qs ? `?${qs}` : ''}`;
  });

  // ── Carousel ──

  carouselTransform(slide: number): string {
    return `translateX(-${slide * 100}%)`;
  }

  currentSlide(propId: number): number {
    return this.carouselSlides().get(propId) ?? 0;
  }

  goToSlide(propId: number, index: number, total: number) {
    const clamped = ((index % total) + total) % total;
    const next = new Map(this.carouselSlides());
    next.set(propId, clamped);
    this.carouselSlides.set(next);
  }

  startAutoPlay(propId: number, total: number) {
    this.stopAutoPlay(propId);
    const timer = setInterval(() => {
      const current = this.carouselSlides().get(propId) ?? 0;
      this.goToSlide(propId, current + 1, total);
    }, 4000);
    this._carouselTimers.set(propId, timer);
  }

  stopAutoPlay(propId: number) {
    const timer = this._carouselTimers.get(propId);
    if (timer) {
      clearInterval(timer);
      this._carouselTimers.delete(propId);
    }
  }

  // ── Hover del carrusel: autoplay + revelar flechas del carrusel compartido ──

  /** Hoteles con el mouse encima: el componente compartido muestra sus
   *  flechas (modo reveal) solo mientras el card está hovereado. */
  readonly hoveredHotels = signal<Set<number>>(new Set());

  onImageEnter(propId: number, total: number): void {
    this.hoveredHotels.update((s) => new Set(s).add(propId));
    this.startAutoPlay(propId, total);
  }

  onImageLeave(propId: number): void {
    this.hoveredHotels.update((s) => {
      const next = new Set(s);
      next.delete(propId);
      return next;
    });
    this.stopAutoPlay(propId);
  }

  // ── Display ──

  hotelFlags(propId: number): ComparisonFlags | undefined {
    return this.comparisonResults().get(propId);
  }

  amenityIcon = amenityIcon;
  carouselImages = carouselImages;
  categorizeAmenities = categorizeAmenities;
  minRate = minRate;
  policyIcon = policyIcon;

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

  handleImageError(key: string) {
    const current = this.imageErrors();
    const next = new Set(current);
    next.add(key);
    this.imageErrors.set(next);
  }
}
