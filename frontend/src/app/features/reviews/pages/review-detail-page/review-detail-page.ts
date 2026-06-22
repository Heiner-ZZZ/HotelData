import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { switchMap, tap } from 'rxjs';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ReviewDetailViewModel } from '../../models/reviews.model';
import { ReviewsApiService } from '../../services/reviews-api.service';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-review-detail-page',
  imports: [ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, StatusBadgeComponent, FormsModule],
  templateUrl: './review-detail-page.html',
  styleUrl: './review-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReviewDetailPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly reviewsApi = inject(ReviewsApiService);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly review = signal<ReviewDetailViewModel | null>(null);
  readonly actionMessage = signal<string | null>(null);
  readonly actionError = signal<string | null>(null);
  readonly staffResponseText = signal('');

  constructor() {
    this.activatedRoute.paramMap
      .pipe(
        switchMap(params => {
          this.viewState.set('loading');
          return this.reviewsApi.getReviewDetail(params.get('reviewId')!);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: data => {
          this.review.set(data);
          this.staffResponseText.set(data.staffResponse || '');
          this.viewState.set('success');
        },
        error: () => this.viewState.set('error'),
      });
  }

  moderate(status: string) {
    this.actionError.set(null);
    this.actionMessage.set(null);
    const reason = status === 'rejected' ? 'Incumple políticas de contenido' : '';
    this.reviewsApi.moderateReview(this.review()!.id, status, reason).subscribe({
      next: () => {
        this.actionMessage.set(`Reseña ${status === 'approved' ? 'aprobada' : 'rechazada'} correctamente.`);
        this.review.update(r => r ? { ...r, moderationStatus: status } : r);
      },
      error: () => this.actionError.set('No se pudo moderar la reseña. Intenta nuevamente.'),
    });
  }

  respond() {
    this.actionError.set(null);
    this.actionMessage.set(null);
    if (!this.staffResponseText().trim()) return;
    this.reviewsApi.respondToReview(this.review()!.id, this.staffResponseText().trim()).subscribe({
      next: () => {
        this.actionMessage.set('Respuesta guardada correctamente.');
      },
      error: () => this.actionError.set('No se pudo guardar la respuesta. Intenta nuevamente.'),
    });
  }

  goBack() {
    void this.router.navigate(['/management/reviews']);
  }
}
