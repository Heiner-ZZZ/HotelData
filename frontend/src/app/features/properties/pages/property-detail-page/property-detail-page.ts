import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { map, switchMap } from 'rxjs';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { PropertyFactsPanelComponent } from '../../components/property-facts-panel/property-facts-panel';
import type { PropertyDetailViewModel } from '../../models/properties.model';
import { PropertiesApiService } from '../../services/properties-api.service';
import { ReviewsApiService } from '../../../reviews/services/reviews-api.service';

@Component({
  selector: 'app-property-detail-page',
  imports: [
    ErrorStateComponent,
    FormsModule,
    LoadingStateComponent,
    PageHeaderComponent,
    PropertyFactsPanelComponent,
    RouterLink,
    StatusBadgeComponent,
  ],
  templateUrl: './property-detail-page.html',
  styleUrl: './property-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PropertyDetailPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(PropertiesApiService);
  private readonly reviewsApi = inject(ReviewsApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<PropertyDetailViewModel | null>(null);

  // RF-006: Top approved reviews
  readonly reviews = signal<Array<{
    id: string;
    rating: number;
    title: string;
    comment: string;
    userName: string;
    createdAt: string;
    staffResponse: string | null;
  }>>([]);
  readonly reviewsLoaded = signal(false);
  readonly reviewsError = signal(false);

  constructor() {
    this.route.paramMap
      .pipe(
        map((params) => Number(params.get('propertyId'))),
        switchMap((propId) => {
          this.viewState.set('loading');
          return this.api.getPropertyDetail(propId);
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (vm) => {
          this.viewModel.set(vm);
          this.viewState.set('success');
          // Load approved reviews in background
          this.loadReviews(vm.propId);
        },
        error: () => this.viewState.set('error')
      });
  }

  private loadReviews(propId: number) {
    this.reviewsApi.getHotelReviews(propId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (items) => {
        this.reviews.set(items.map(r => ({
          id: r._id,
          rating: r.rating,
          title: r.title,
          comment: r.comment,
          userName: r.user_display_name || 'Huésped',
          createdAt: r.created_at || '',
          staffResponse: r.staff_response ?? null,
        })));
        this.reviewsLoaded.set(true);
      },
      error: () => {
        this.reviewsLoaded.set(true);
        this.reviewsError.set(true);
      },
    });
  }
}
