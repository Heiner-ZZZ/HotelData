import { AfterViewInit, ChangeDetectionStrategy, Component, computed, DestroyRef, inject, OnDestroy, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { map, switchMap } from 'rxjs';
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
export class HotelComparePageComponent implements OnDestroy {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly compareApi = inject(HotelCompareApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly compareData = signal<HotelCompareData | null>(null);
  readonly propIds = signal<number[]>([]);
  readonly expandedRooms = signal<Set<number>>(new Set());
  readonly imageErrors = signal<Set<string>>(new Set());
  readonly carouselSlides = signal<Map<number, number>>(new Map());
  private readonly _carouselTimers = new Map<number, ReturnType<typeof setInterval>>();

  readonly comparisonResults = computed(() => {
    const items = this.compareData()?.items;
    return items ? computeComparisonFlags(items) : new Map<number, ComparisonFlags>();
  });

  readonly minRateValue = computed(() => {
    const items = this.compareData()?.items;
    return items ? minRate(items) : '—';
  });

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
        },
        error: () => this.viewState.set('error'),
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
    return `/search${existing.length ? `?compare_ids=${existing.join(',')}` : ''}`;
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

  ngOnDestroy() {
    for (const timer of this._carouselTimers.values()) {
      clearInterval(timer);
    }
    this._carouselTimers.clear();
  }
}
