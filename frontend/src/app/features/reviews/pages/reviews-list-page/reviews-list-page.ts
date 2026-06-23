import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { SlicePipe } from '@angular/common';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ReviewsListViewModel } from '../../models/reviews.model';
import { ReviewsApiService } from '../../services/reviews-api.service';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-reviews-list-page',
  imports: [SlicePipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, StatusBadgeComponent, RouterLink, FormsModule],
  templateUrl: './reviews-list-page.html',
  styleUrl: './reviews-list-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReviewsListPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly reviewsApi = inject(ReviewsApiService);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<ReviewsListViewModel | null>(null);
  readonly filterStatus = signal<string>('');

  constructor() {
    this.activatedRoute.queryParamMap
      .pipe(
        map(params => ({
          page: Number(params.get('page') ?? '1'),
          status: params.get('status') ?? '',
        })),
        distinctUntilChanged((a, b) => a.page === b.page && a.status === b.status),
        switchMap(({ page, status }) => {
          this.filterStatus.set(status);
          this.viewState.set('loading');
          return this.reviewsApi.getReviews(page, status || undefined);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: data => {
          this.data.set(data);
          this.viewState.set(data.items.length ? 'success' : 'empty');
        },
        error: () => this.viewState.set('error'),
      });
  }

  setFilter(status: string) {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { status: status || null, page: null },
      queryParamsHandling: 'merge',
    });
  }

  goToPage(page: number) {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { page: page > 1 ? page : null },
      queryParamsHandling: 'merge',
    });
  }
}
