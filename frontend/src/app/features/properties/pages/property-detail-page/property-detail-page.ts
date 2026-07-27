import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { rxResource } from '@angular/core/rxjs-interop';
import { of } from 'rxjs';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { map } from 'rxjs';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PropertyFactsPanelComponent } from '../../components/property-facts-panel/property-facts-panel';
import { OperationalCalendarComponent } from '../../components/operational-calendar/operational-calendar';
import type { OperationalCalendarData } from '../../components/operational-calendar/operational-calendar';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { PropertyDetailViewModel } from '../../models/properties.model';
import type { PropertyDetailResponseDto } from '../../models/properties.dto';
import { ReviewsApiService } from '../../../reviews/services/reviews-api.service';
import type { ReviewsListDto } from '../../../reviews/models/reviews.dto';
import { mapPropertyDetailResponse } from '../../mappers/properties.mapper';

@Component({
  selector: 'app-property-detail-page',
  imports: [
    ErrorStateComponent,
    LoadingStateComponent,
    OperationalCalendarComponent,
    PropertyFactsPanelComponent,
    RouterLink,
  ],
  templateUrl: './property-detail-page.html',
  styleUrl: './property-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PropertyDetailPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly reviewsApi = inject(ReviewsApiService);

  readonly propId = toSignal(
    this.route.paramMap.pipe(map((params) => Number(params.get('propertyId')))),
    { initialValue: 0 }
  );

  readonly detailResource = httpResource<PropertyDetailViewModel>(() => {
    const propId = this.propId();
    return propId ? `/api/management/properties/${propId}` : undefined;
  }, {
    parse: (dto) => mapPropertyDetailResponse(dto as PropertyDetailResponseDto),
  });

  readonly viewState = computed<ViewState>(() => {
    if (this.detailResource.isLoading()) return 'loading';
    if (this.detailResource.error()) return 'error';
    return this.detailResource.value() ? 'success' : 'loading';
  });

  readonly opsCircumference = computed(() => {
    const r = 52;
    return 2 * Math.PI * r;
  });

  readonly opsOffset = computed(() => {
    const score = this.detailResource.value()?.operationalScore ?? 0;
    const circ = 2 * Math.PI * 52;
    return circ - (circ * score) / 100;
  });

  // Operational calendar — httpResource auto-fires when detail loads or year/month change
  readonly calendarResource = httpResource<OperationalCalendarData>(() => {
    const propId = this.detailResource.value()?.propId ?? this.propId();
    const year = this.calendarYear();
    const month = this.calendarMonth();
    if (!propId || !year || !month) return undefined;
    return `/api/management/properties/${propId}/operational-calendar?year=${year}&month=${month}`;
  }, {
    /**
     * Tolerant passthrough mapper. `OperationalCalendarData` is already the
     * view-model type consumed downstream. If a future refactor introduces
     * a snake-shape DTO, replace this passthrough with an explicit
     * snake→camel mapper (per the round-6/7 canonical pattern).
     */
    parse: (dto) => dto as OperationalCalendarData,
  });
  readonly calendarData = computed(() => this.calendarResource.value() ?? null);
  readonly calendarLoading = this.calendarResource.isLoading;
  readonly calendarYear = signal(new Date().getFullYear());
  readonly calendarMonth = signal(new Date().getMonth() + 1);

  readonly weekStart = signal(this._mondayOfToday());

  private _mondayOfToday(): string {
    const d = new Date();
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    d.setDate(diff);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }

  prevWeek() {
    const d = new Date(this.weekStart());
    d.setDate(d.getDate() - 7);
    this._setWeekAndLoad(d);
  }

  nextWeek() {
    const d = new Date(this.weekStart());
    d.setDate(d.getDate() + 7);
    this._setWeekAndLoad(d);
  }

  private _setWeekAndLoad(d: Date) {
    const newY = d.getFullYear();
    const newM = d.getMonth() + 1;
    this.weekStart.set(`${newY}-${String(newM).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`);
    this.calendarYear.set(newY);
    this.calendarMonth.set(newM);
  }

  // RF-006: Approved reviews — rxResource fires when detail or page changes
  readonly reviewsPageSize = 10;
  readonly reviewsPage = signal(1);
  readonly reviewsResource = rxResource<ReviewsListDto | undefined, { propId: number; page: number } | undefined>({
    params: () => {
      const propId = this.detailResource.value()?.propId ?? this.propId();
      return propId ? { propId, page: this.reviewsPage() } : undefined;
    },
    stream: ({ params }) => {
      if (!params) return of(undefined);
      return this.reviewsApi.getHotelReviews(params.propId, params.page, this.reviewsPageSize);
    },
  });
  readonly reviews = computed(() => (this.reviewsResource.value()?.items ?? []).map(r => ({
    id: r.id,
    rating: r.rating,
    title: r.title,
    comment: r.comment,
    userName: r.user_display_name || 'Huésped',
    createdAt: r.created_at || '',
    staffResponse: r.staff_response ?? null,
  })));
  readonly reviewsLoaded = computed(() => !this.reviewsResource.isLoading());
  readonly reviewsError = computed(() => !!this.reviewsResource.error());
  readonly reviewsHasNext = computed(() => this.reviewsResource.value()?.has_next ?? false);
  readonly reviewsHasPrev = computed(() => this.reviewsResource.value()?.has_prev ?? false);

  nextReviewsPage(): void {
    if (this.reviewsHasNext()) this.reviewsPage.update(p => p + 1);
  }

  prevReviewsPage(): void {
    if (this.reviewsHasPrev()) this.reviewsPage.update(p => Math.max(1, p - 1));
  }

  constructor() {
    // Reset reviews page when the route property changes
    effect(() => {
       
      this.propId();
      this.reviewsPage.set(1);
    });
  }
}
