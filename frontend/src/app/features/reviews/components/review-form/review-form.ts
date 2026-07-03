import { ChangeDetectionStrategy, Component, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DatePipe } from '@angular/common';

import { ReviewsApiService } from '../../services/reviews-api.service';

export interface ReviewFormResult {
  success: boolean;
  message: string;
}

@Component({
  selector: 'app-review-form',
  standalone: true,
  imports: [FormsModule, DatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="review-form">
      <!-- ═══ Booking Context Card ═══ -->
      @if (hotelName() || roomLabel() || checkInDate() || checkOutDate()) {
        <div class="booking-context">
          @if (hotelName()) {
            <div class="context-row">
              <span class="material-symbols-outlined context-icon">business</span>
              <span class="context-value">{{ hotelName() }}</span>
            </div>
          }
          <div class="context-details">
            @if (roomLabel()) {
              <div class="context-chip">
                <span class="material-symbols-outlined chip-icon">meeting_room</span>
                {{ roomLabel() }}
              </div>
            }
            @if (checkInDate() && checkOutDate()) {
              <div class="context-chip">
                <span class="material-symbols-outlined chip-icon">date_range</span>
                {{ checkInDate() | date:'dd MMM' }} — {{ checkOutDate() | date:'dd MMM yyyy' }}
              </div>
            }
          </div>
        </div>
      }

      <!-- ═══ Overall Rating ═══ -->
      <div class="rating-section">
        <div class="rating-label">Calificación general</div>
        <div class="star-row big">
          @for (star of [1,2,3,4,5]; track star) {
            <button type="button" class="star-btn" (click)="overallRating.set(star)"
              [class.active]="star <= overallRating()"
              [class.hover]="star <= hoverRating()"
              (mouseenter)="hoverRating.set(star)"
              (mouseleave)="hoverRating.set(0)">
              <span class="material-symbols-outlined star-icon">
                {{ star <= (hoverRating() || overallRating()) ? 'star' : 'star_border' }}
              </span>
            </button>
          }
        </div>
      </div>

      <!-- ═══ Title ═══ -->
      <div class="title-section">
        <label class="title-label" for="reviewTitle">
          Título de la reseña <small>(opcional)</small>
        </label>
        <input
          id="reviewTitle"
          type="text"
          [(ngModel)]="title"
          placeholder="Ej: Excelente estancia, volveremos pronto"
          class="title-input"
        />
      </div>

      <!-- ═══ Service Ratings ═══ -->
      <div class="service-section">
        <div class="service-section-label">Valoración por servicios</div>
        <p class="service-section-hint">¿Qué tal estuvo cada servicio?</p>

        <div class="service-ratings">
          @for (svc of services; track svc.key) {
            <div class="service-row">
              <div class="service-info">
                <span class="material-symbols-outlined service-icon">{{ svc.icon }}</span>
                <span class="service-name">{{ svc.label }}</span>
              </div>
              <button type="button" class="face-btn"
                [class.face-good]="(serviceRatings()[svc.key] ?? 0) >= 4"
                [class.face-neutral]="(serviceRatings()[svc.key] ?? 0) === 3"
                [class.face-bad]="(serviceRatings()[svc.key] ?? 0) >= 1 && (serviceRatings()[svc.key] ?? 0) <= 2"
                [class.face-none]="(serviceRatings()[svc.key] ?? 0) === 0"
                (click)="cycleServiceRating(svc.key)"
                [title]="getFaceLabel(serviceRatings()[svc.key])">
                <span class="material-symbols-outlined face-icon">
                  {{ getFaceIcon(serviceRatings()[svc.key]) }}
                </span>
                <span class="face-label">{{ getFaceLabel(serviceRatings()[svc.key]) }}</span>
              </button>
            </div>
          }
        </div>
      </div>

      <!-- ═══ Description ═══ -->
      <div class="desc-section">
        <label class="desc-label" for="reviewComment">Comentario general <small>(opcional)</small></label>
        <textarea
          id="reviewComment"
          [(ngModel)]="comment"
          rows="3"
          placeholder="Cuéntanos brevemente cómo fue tu estancia..."
          class="desc-textarea"
        ></textarea>
      </div>

      <!-- ═══ Submit ═══ -->
      @if (error()) {
        <div class="error-msg">{{ error() }}</div>
      }
      <button type="button" class="submit-btn" (click)="submit()" [disabled]="submitting() || overallRating() === 0">
        @if (submitting()) {
          <span class="material-symbols-outlined spin">sync</span>
          Enviando…
        } @else {
          <span class="material-symbols-outlined">send</span>
          Enviar reseña
        }
      </button>
    </div>
  `,
  styles: [`
    .review-form {
      padding: 20px;
      max-width: 480px;
    }

    /* ─── Booking Context Card ─── */
    .booking-context {
      background: linear-gradient(135deg, #f0f4ff 0%, #faf5ff 100%);
      border: 1px solid #e0e7ff;
      border-radius: 12px;
      padding: 14px 16px;
      margin-bottom: 24px;

      .context-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
      }
      .context-icon { font-size: 20px; color: #6366f1; }
      .context-value { font-size: 15px; font-weight: 600; color: #1e1b4b; }

      .context-details {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }
      .context-chip {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 10px;
        background: white;
        border: 1px solid #e0e7ff;
        border-radius: 999px;
        font-size: 12px;
        color: #4338ca;
      }
      .chip-icon { font-size: 14px; }
    }

    /* ─── Rating ─── */
    .rating-section {
      margin-bottom: 20px;
      text-align: center;
    }
    .rating-label {
      font-size: 14px;
      font-weight: 600;
      color: #0f172a;
      margin-bottom: 8px;
    }
    .star-row {
      display: flex;
      justify-content: center;
      gap: 4px;
      &.big .star-btn { padding: 4px 2px; }
    }
    .star-btn {
      background: none;
      border: none;
      cursor: pointer;
      padding: 2px;
      border-radius: 4px;
      transition: transform 0.1s;
      &:hover { transform: scale(1.15); }
      &.small { padding: 2px; }
    }
    .star-icon {
      font-size: 28px;
      color: #d1d5db;
      transition: color 0.15s;
      &.small-icon { font-size: 20px; }
    }
    .star-btn.active .star-icon, .star-btn.hover .star-icon { color: #f59e0b; }

    /* ─── Service Faces ─── */
    .face-btn {
      display: inline-flex;
      flex-direction: column;
      align-items: center;
      gap: 2px;
      background: none;
      border: none;
      cursor: pointer;
      padding: 4px 12px;
      border-radius: 8px;
      transition: all 0.15s;
      &:hover { background: #f1f5f9; transform: scale(1.05); }
    }
    .face-icon { font-size: 28px; transition: color 0.2s; }
    .face-label { font-size: 9px; font-weight: 500; white-space: nowrap; }
    .face-bad .face-icon { color: #ef4444; }
    .face-bad .face-label { color: #dc2626; }
    .face-neutral .face-icon { color: #f59e0b; }
    .face-neutral .face-label { color: #d97706; }
    .face-good .face-icon { color: #22c55e; }
    .face-good .face-label { color: #16a34a; }
    .face-none .face-icon { color: #d1d5db; }
    .face-none .face-label { color: #9ca3af; }

    /* ─── Title ─── */
    .title-section {
      margin-bottom: 20px;
    }
    .title-label {
      display: block;
      font-size: 13px;
      font-weight: 500;
      color: #475569;
      margin-bottom: 6px;
      small { font-weight: 400; color: #94a3b8; }
    }
    .title-input {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      font-size: 13px;
      font-family: inherit;
      box-sizing: border-box;
      &:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.15); }
      &::placeholder { color: #94a3b8; }
    }

    /* ─── Services ─── */
    .service-section {
      margin-bottom: 24px;
    }
    .service-section-label {
      font-size: 13px;
      font-weight: 600;
      color: #475569;
      margin-bottom: 2px;
    }
    .service-section-hint {
      font-size: 12px;
      color: #94a3b8;
      margin: 0 0 12px;
    }
    .service-ratings {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .service-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      background: #fafafa;
      border: 1px solid #f1f5f9;
      border-radius: 10px;
    }
    .service-info {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .service-icon { font-size: 20px; color: #64748b; }
    .service-name { font-size: 13px; font-weight: 500; color: #334155; }

    /* ─── Description ─── */
    .desc-section {
      margin-bottom: 20px;
    }
    .desc-label {
      display: block;
      font-size: 13px;
      font-weight: 500;
      color: #475569;
      margin-bottom: 6px;
      small { font-weight: 400; color: #94a3b8; }
    }
    .desc-textarea {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      font-size: 13px;
      font-family: inherit;
      resize: vertical;
      min-height: 60px;
      box-sizing: border-box;
      &:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.15); }
      &::placeholder { color: #94a3b8; }
    }

    /* ─── Error ─── */
    .error-msg {
      padding: 10px 12px;
      background: #fef2f2;
      color: #991b1b;
      border: 1px solid #fecaca;
      border-radius: 8px;
      font-size: 12px;
      margin-bottom: 12px;
    }

    /* ─── Submit ─── */
    .submit-btn {
      width: 100%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 12px 24px;
      border: none;
      border-radius: 10px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      background: #2563eb;
      color: white;
      transition: all 0.15s;
      &:hover:not(:disabled) { background: #1d4ed8; }
      &:disabled { opacity: 0.5; cursor: not-allowed; }
    }

    .spin { animation: spin 1s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }
  `],
})
export class ReviewFormComponent {
  private readonly reviewsApi = inject(ReviewsApiService);

  /** The booking ID being reviewed */
  readonly bookingId = input.required<string>();
  /** The property ID being reviewed */
  readonly propId = input.required<number>();

  /** Booking context for display (optional - PMS/CRM data) */
  readonly hotelName = input<string>('');
  readonly roomLabel = input<string>('');
  readonly checkInDate = input<string>('');
  readonly checkOutDate = input<string>('');

  /** Emitted when the review is submitted successfully */
  readonly reviewCreated = output<ReviewFormResult>();

  readonly overallRating = signal(0);
  readonly hoverRating = signal(0);
  readonly title = signal('');
  readonly comment = signal('');
  readonly submitting = signal(false);
  readonly error = signal<string | null>(null);

  readonly serviceRatings = signal<Record<string, number>>({
    housekeeping: 0,
    food_beverage: 0,
    staff: 0,
  });

  readonly services = [
    { key: 'housekeeping', label: 'Housekeeping', icon: 'cleaning_services' },
    { key: 'food_beverage', label: 'F&B', icon: 'restaurant' },
    { key: 'staff', label: 'Staff', icon: 'concierge' },
  ];

  setServiceRating(key: string, value: number) {
    this.serviceRatings.update(r => ({ ...r, [key]: value }));
  }

  cycleServiceRating(key: string) {
    const current = this.serviceRatings()[key] ?? 0;
    const next = current >= 5 ? 0 : current + 1;
    this.setServiceRating(key, next);
  }

  getFaceIcon(rating: number): string {
    if (rating <= 0) return 'sentiment_neutral';
    const icons = ['sentiment_very_dissatisfied', 'sentiment_dissatisfied', 'sentiment_neutral', 'sentiment_satisfied', 'sentiment_very_satisfied'];
    return icons[rating - 1] || 'sentiment_neutral';
  }

  getFaceLabel(rating: number): string {
    const labels = ['Sin calificar', 'Muy malo', 'Malo', 'Regular', 'Bueno', 'Excelente'];
    return labels[rating] || labels[0];
  }

  submit() {
    if (this.overallRating() === 0) return;
    this.submitting.set(true);
    this.error.set(null);

    const sr = this.serviceRatings();
    const hk = sr['housekeeping'] ?? 0;
    const fb = sr['food_beverage'] ?? 0;
    const st = sr['staff'] ?? 0;
    const hasServiceRatings = hk > 0 || fb > 0 || st > 0;

    const payload: any = {
      booking_id: this.bookingId(),
      prop_id: this.propId(),
      rating: this.overallRating(),
      title: this.title(),
      comment: this.comment(),
    };

    if (hasServiceRatings) {
      payload.service_ratings = {
        housekeeping: hk > 0 ? hk : null,
        food_beverage: fb > 0 ? fb : null,
        staff: st > 0 ? st : null,
      };
    }

    this.reviewsApi.createReview(payload).subscribe({
      next: () => {
        this.reviewCreated.emit({ success: true, message: 'Reseña enviada correctamente. ¡Gracias!' });
        this.submitting.set(false);
      },
      error: (err) => {
        const detail = err?.error?.detail || 'Error al enviar la reseña. Intenta nuevamente.';
        this.error.set(detail);
        this.submitting.set(false);
      },
    });
  }
}
