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
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ReviewsListViewModel } from '../../models/reviews.model';
import { ReviewsApiService } from '../../services/reviews-api.service';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-reviews-list-page',
  imports: [SlicePipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, StatusBadgeComponent, PropertySelectorComponent, RouterLink, FormsModule],
  templateUrl: './reviews-list-page.html',
  styleUrl: './reviews-list-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReviewsListPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly reviewsApi = inject(ReviewsApiService);
  private readonly router = inject(Router);
  readonly propertyCtx = inject(PropertyContextService);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<ReviewsListViewModel | null>(null);
  readonly filterStatus = signal<string>('');
  readonly selectedPropId = signal(0);
  readonly selectedLabel = signal('');

  constructor() {
    this.activatedRoute.queryParamMap
      .pipe(
        map(params => ({
          page: Number(params.get('page') ?? '1'),
          status: params.get('status') ?? '',
          propId: Number(params.get('prop_id') ?? '0'),
        })),
        distinctUntilChanged((a, b) => a.page === b.page && a.status === b.status && a.propId === b.propId),
        switchMap(({ page, status, propId }) => {
          this.filterStatus.set(status);
          this.selectedPropId.set(propId);
          // Resolve label from assigned properties or fall back to empty
          const label = propId
            ? this.propertyCtx.assignedProperties().find(p => p.propId === propId)?.label ?? ''
            : '';
          this.selectedLabel.set(label);
          this.viewState.set('loading');
          return this.reviewsApi.getReviews(page, status || undefined, propId || undefined);
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

  onPropertySelected(event: { propId: number; label: string }) {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { prop_id: event.propId || null, page: null },
      queryParamsHandling: 'merge',
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
