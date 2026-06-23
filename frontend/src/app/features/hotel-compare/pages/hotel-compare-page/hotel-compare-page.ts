import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { map, switchMap } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { HotelCompareData, HotelCompareItem } from '../../models/hotel-compare.model';
import type { HotelCompareRoomType } from '../../models/hotel-compare.model';
import { HotelCompareApiService } from '../../services/hotel-compare-api.service';

@Component({
  selector: 'app-hotel-compare-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    RouterLink,
  ],
  templateUrl: './hotel-compare-page.html',
  styleUrl: './hotel-compare-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HotelComparePageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly compareApi = inject(HotelCompareApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly compareData = signal<HotelCompareData | null>(null);
  readonly propIds = signal<number[]>([]);

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
        error: () => {
          this.viewState.set('error');
        },
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
    return `/search` + (existing.length ? `?compare_ids=${existing.join(',')}` : '');
  });

  amenityList(text: string | undefined | null): string[] {
    if (!text) return [];
    return text.split(',').map((t) => t.trim()).filter(Boolean);
  }
}
