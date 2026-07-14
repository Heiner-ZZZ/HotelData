import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal, untracked } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { map } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { toSignal } from '@angular/core/rxjs-interop';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PropertyFactsPanelComponent } from '../../components/property-facts-panel/property-facts-panel';
import { OperationalCalendarComponent } from '../../components/operational-calendar/operational-calendar';
import type { OperationalCalendarData } from '../../components/operational-calendar/operational-calendar';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { PropertyDetailViewModel } from '../../models/properties.model';
import type { PropertyDetailResponseDto } from '../../models/properties.dto';
import { PropertiesApiService } from '../../services/properties-api.service';
import { ReviewsApiService } from '../../../reviews/services/reviews-api.service';
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
  private readonly api = inject(PropertiesApiService);
  private readonly reviewsApi = inject(ReviewsApiService);
  private readonly destroyRef = inject(DestroyRef);

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

  // Operational calendar — single week view
  readonly calendarData = signal<OperationalCalendarData | null>(null);
  readonly calendarLoading = signal(false);
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

  private _loadCalendar(propId: number, year: number, month: number) {
    this.calendarLoading.set(true);
    this.api.getOperationalCalendar(propId, year, month).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (data) => {
        this.calendarData.set(data as OperationalCalendarData);
        this.calendarLoading.set(false);
      },
      error: () => this.calendarLoading.set(false),
    });
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
    const y = this.calendarYear();
    const m = this.calendarMonth();
    this.weekStart.set(`${newY}-${String(newM).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`);
    if (newY !== y || newM !== m) {
      this.calendarYear.set(newY);
      this.calendarMonth.set(newM);
      this._loadCalendar(this.detailResource.value()?.propId ?? this.propId(), newY, newM);
    }
  }

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
    effect(() => {
      const vm = this.detailResource.value();
      if (!vm) return;
      const propId = vm.propId;
      const year = untracked(() => this.calendarYear());
      const month = untracked(() => this.calendarMonth());
      this._loadCalendar(propId, year, month);
      this.loadReviews(propId);
    });
  }

  private loadReviews(propId: number) {
    this.reviewsApi.getHotelReviews(propId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (items) => {
        this.reviews.set((items as any[]).map(r => ({
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
