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

  // RF-005: RBAC state — will be populated from auth context
  readonly userRole = signal<string | null>(null);
  readonly userPermissions = signal<Set<string>>(new Set());

  // Rejection reason input
  readonly rejectionReason = signal('');

  // Confirmation dialog
  readonly confirmAction = signal<{ type: 'approve' | 'reject'; label: string; status: string } | null>(null);

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
          // Resolve user role from auth context (set by middleware)
          this.resolveUserRole();
        },
        error: () => this.viewState.set('error'),
      });
  }

  private resolveUserRole() {
    // Read user info from a global auth signal if available,
    // otherwise default to allowing all actions (fallback — backend enforces)
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const win = window as any;
      if (win.__hoteldata_user) {
        this.userRole.set(win.__hoteldata_user.primary_role || null);
        if (win.__hoteldata_user.permissions) {
          this.userPermissions.set(new Set(win.__hoteldata_user.permissions));
        }
      }
    } catch {
      // fallback: backend enforces RBAC
    }
  }

  // RF-005: Check if user can moderate
  get canModerate(): boolean {
    const role = this.userRole();
    if (!role) return true; // fallback: backend enforces
    return role === 'super_admin' || role === 'marketing_hotelero' || this.userPermissions().has('reviews.moderate');
  }

  // RF-006: Check if user can respond
  get canRespond(): boolean {
    const role = this.userRole();
    if (!role) return true; // fallback: backend enforces
    return role === 'hotel_partner' || role === 'super_admin' || role === 'admin_sistema';
  }

  // Ask confirmation before moderating
  requestModerate(status: string) {
    const r = this.review();
    if (!r) return;
    // If already moderated and not pending, block (idempotent)
    if (r.moderationStatus !== 'pending') return;
    if (status === 'rejected' && !this.rejectionReason().trim()) {
      this.actionError.set('Debes ingresar un motivo para rechazar la reseña.');
      return;
    }
    this.confirmAction.set({
      type: status === 'approved' ? 'approve' : 'reject',
      label: status === 'approved' ? 'aprobar' : 'rechazar',
      status,
    });
  }

  confirmModerate() {
    const action = this.confirmAction();
    if (!action) return;
    this.confirmAction.set(null);
    this.actionError.set(null);
    this.actionMessage.set(null);
    const reason = action.status === 'rejected' ? this.rejectionReason().trim() : '';
    this.reviewsApi.moderateReview(this.review()!.id, action.status, reason).subscribe({
      next: () => {
        this.actionMessage.set(`Reseña ${action.label}da correctamente.`);
        this.review.update(r => r ? { ...r, moderationStatus: action.status } : r);
        this.rejectionReason.set('');
      },
      error: (err) => {
        const detail = err?.error?.detail || 'No se pudo moderar la reseña. Intenta nuevamente.';
        this.actionError.set(detail);
      },
    });
  }

  cancelModerate() {
    this.confirmAction.set(null);
  }

  respond() {
    this.actionError.set(null);
    this.actionMessage.set(null);
    if (!this.staffResponseText().trim()) return;
    this.reviewsApi.respondToReview(this.review()!.id, this.staffResponseText().trim()).subscribe({
      next: () => {
        this.actionMessage.set('Respuesta guardada correctamente.');
      },
      error: (err) => {
        const detail = err?.error?.detail || 'No se pudo guardar la respuesta. Intenta nuevamente.';
        this.actionError.set(detail);
      },
    });
  }

  goBack() {
    void this.router.navigate(['/management/reviews']);
  }
}
