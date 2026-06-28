import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { map, switchMap, tap } from 'rxjs';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PropertyFactsPanelComponent } from '../../components/property-facts-panel/property-facts-panel';
import { OperationalCalendarComponent } from '../../components/operational-calendar/operational-calendar';
import type { OperationalCalendarData } from '../../components/operational-calendar/operational-calendar';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { PropertyDetailViewModel } from '../../models/properties.model';
import { PropertiesApiService } from '../../services/properties-api.service';
import { ReviewsApiService } from '../../../reviews/services/reviews-api.service';

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

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<PropertyDetailViewModel | null>(null);

  readonly opsCircumference = computed(() => {
    const r = 52;
    return 2 * Math.PI * r;
  });

  readonly opsOffset = computed(() => {
    const score = this.viewModel()?.operationalScore ?? 0;
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
        this.calendarData.set(data);
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
      this._loadCalendar(this.viewModel()!.propId, newY, newM);
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
          // Load operational calendar in background
          this._loadCalendar(vm.propId, this.calendarYear(), this.calendarMonth());
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
