import { HttpErrorResponse, httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CompareMapComponent } from './components/compare-map';
import { amenityIcon, carouselImages, categorizeAmenities, computeComparisonFlags, minRate, policyIcon } from './hotel-compare.helpers';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ComparisonFlags, HotelCompareData } from '../../models/hotel-compare.model';
import { HotelCompareApiService } from '../../services/hotel-compare-api.service';

@Component({
  selector: 'app-hotel-compare-page',
  imports: [RouterLink, CompareMapComponent],
  templateUrl: './hotel-compare-page.html',
  styleUrl: './hotel-compare-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HotelComparePageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly compareApi = inject(HotelCompareApiService);
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
    const v = this.compareResource.value();
    if (this.compareResource.isLoading() && !v) return 'loading';
    const err = this.compareResource.error();
    if (err instanceof HttpErrorResponse) return err.status === 404 ? 'empty' : 'error';
    if (err) return 'error';
    return v?.items.length ? 'success' : 'empty';
  });

  readonly compareData = computed(() => this.compareResource.value() ?? null);
  readonly propIds = computed(() => this.propIdsParam());
  readonly expandedRooms = signal<Set<number>>(new Set());
  readonly imageErrors = signal<Set<string>>(new Set());
  readonly carouselSlides = signal<Map<number, number>>(new Map());
  private readonly _carouselTimers = new Map<number, ReturnType<typeof setInterval>>();

  /** httpResource — auto-fetches whenever URL params change. */
  readonly compareResource = httpResource<HotelCompareData>(() => {
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
    const qs = params.toString();
    return qs
      ? `/api/hostels/compare?ids=${ids.join(',')}&${qs}`
      : `/api/hostels/compare?ids=${ids.join(',')}`;
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
