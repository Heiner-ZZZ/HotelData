import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';

import { getErrorStatus, getErrorMessage } from '../../../../shared/utils/http-error.util';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ReviewDetailViewModel } from '../../models/reviews.model';
import type { ReviewDetailDto } from '../../models/reviews.dto';
import { mapReviewDetail } from '../../mappers/reviews.mapper';
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
  private readonly reviewsApi = inject(ReviewsApiService);
  private readonly router = inject(Router);

  // ── Reactive route param — httpResource re-fires when this changes ──
  private readonly paramMap = toSignal(this.activatedRoute.paramMap, {
    initialValue: this.activatedRoute.snapshot.paramMap,
  });
  readonly reviewId = computed(() => this.paramMap().get('reviewId') ?? '');

  readonly detailResource = httpResource<ReviewDetailViewModel>(() => {
    const id = this.reviewId();
    return id ? `/api/reviews/${id}` : undefined;
  }, {
    // Canonical mapper: the wire is snake_case (moderation_status,
    // staff_response, user_display_name, …); the ViewModel is camelCase.
    // Skipping this parse left every camelCase field undefined — the badge
    // always rendered 'Pendiente', moderation was silently blocked
    // (r.moderationStatus !== 'pending' with undefined), and the staff
    // response prefill was empty. Same bug class as ownership-user-detail.
    parse: (dto) => mapReviewDetail(dto as ReviewDetailDto),
  });

  readonly review = computed(() => {
    if (this.detailResource.error()) return null;
    return this.detailResource.value() ?? null;
  });

  readonly viewState = computed<ViewState>(() => {
    // error() ANTES de value(): value() lanza cuando el request falló.
    const err = this.detailResource.error();
    if (err) return getErrorStatus(err) === 404 ? 'empty' : 'error';
    const v = this.detailResource.value();
    if (this.detailResource.isLoading() && !v) return 'loading';
    return v ? 'success' : 'loading';
  });

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

  // Id-based init gate: pre-fills staffResponseText + resolves user role only
  // once per fetched review (does NOT overwrite user's edits during a reload).
  private initializedReviewId: string | null = null;

  constructor() {
    effect(() => {
      if (this.detailResource.error()) return;
      const detail = this.detailResource.value();
      if (!detail) return;
      if (this.initializedReviewId === detail.id) return;
      this.initializedReviewId = detail.id;
      // Initial pre-fill from backend (user can edit afterwards freely).
      this.staffResponseText.set(detail.staffResponse || '');
      this.resolveUserRole();
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
    this.reviewsApi.moderateReview(this.review()!.id, action.status, reason, this.review()!.propId).subscribe({        next: () => {
          this.actionMessage.set(`Reseña ${action.label}da correctamente.`);
          // Refetch detail so backend's new moderationStatus / staff_response
          // propagate to the template via `review()` (computed).
          this.detailResource.reload();
          this.rejectionReason.set('');
        },
      error: (err) => {
        this.actionError.set(getErrorMessage(err) || 'No se pudo moderar la reseña. Intenta nuevamente.');
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
    this.reviewsApi.respondToReview(this.review()!.id, this.staffResponseText().trim(), this.review()!.propId).subscribe({
      next: () => {
        this.actionMessage.set('Respuesta guardada correctamente.');
      },
      error: (err) => {
        this.actionError.set(getErrorMessage(err) || 'No se pudo guardar la respuesta. Intenta nuevamente.');
      },
    });
  }

  goBack() {
    void this.router.navigate(['/management/reviews']);
  }
}
