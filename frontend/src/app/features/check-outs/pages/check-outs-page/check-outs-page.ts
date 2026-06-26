import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { API_CONFIG } from '../../../../core/api/api.config';

import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { CheckOutsViewModel } from '../../models/check-outs.model';
import type { CheckOutsDto } from '../../models/check-outs.dto';
import { CheckOutsApiService, type DateHistoryEntry } from '../../services/check-outs-api.service';
import { mapCheckOuts } from '../../mappers/check-outs.mapper';

function todayIso(): string {
  const d = new Date();
  return d.toISOString().slice(0, 10);
}

function shiftDate(iso: string, days: number): string {
  const d = new Date(iso + 'T12:00:00');
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

@Component({
  selector: 'app-check-outs-page',
  imports: [DatePipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent],
  templateUrl: './check-outs-page.html',
  styleUrl: './check-outs-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CheckOutsPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(CheckOutsApiService);
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  // ── Route params as signals ──
  private readonly routeParams = toSignal(
    this.route.queryParamMap.pipe(
      map((params) => ({
        propId: Number(params.get('prop_id') ?? '0'),
        operationDate: params.get('date') || todayIso(),
      })),
      distinctUntilChanged((a, b) => a.propId === b.propId && a.operationDate === b.operationDate),
    ),
    { initialValue: { propId: 0, operationDate: todayIso() } }
  );

  // ── Declarative data fetching ──
  private readonly checkOutsResource = httpResource<CheckOutsDto>(() => {
    const { propId, operationDate } = this.routeParams();
    return `/api/management/check-outs?date=${operationDate}${propId ? `&prop_id=${propId}` : ''}`;
  });

  // ── Derived state ──
  readonly viewState = computed(() => {
    if (this.checkOutsResource.isLoading()) return 'loading' as const;
    if (this.checkOutsResource.error()) return 'error' as const;
    const vm = this.viewModel();
    if (!vm) return 'loading' as const;
    return vm.items.length ? 'success' as const : 'empty' as const;
  });

  readonly viewModel = computed<CheckOutsViewModel | null>(() => {
    const dto = this.checkOutsResource.value();
    return dto ? mapCheckOuts(dto) : null;
  });

  readonly message = signal('');
  readonly errorMessage = signal('');

  // Review modal
  readonly showReviewModal = signal(false);
  readonly reviewBookingId = signal('');
  readonly reviewPropId = signal(0);
  readonly reviewGuestName = signal('');
  readonly reviewRating = signal(0);
  readonly reviewTitle = signal('');
  readonly reviewComment = signal('');
  readonly reviewSubmitting = signal(false);
  readonly reviewError = signal('');
  readonly reviewSuccess = signal(false);

  readonly operationDate = signal(todayIso());

  readonly selectedPropId = computed(() => this.routeParams().propId);
  readonly selectedPropName = computed(() => {
    const vm = this.viewModel();
    const pid = this.selectedPropId();
    if (!vm) return '';
    const opt = vm.propertyOptions.find(p => p.propId === pid);
    return opt?.label ?? '';
  });
  readonly filter = signal('');
  readonly propertyOptions = computed(() => this.viewModel()?.propertyOptions ?? []);
  readonly dropdownOpen = signal(false);

  // More menu (⋮)
  readonly showMenu = signal(false);

  // Date history
  readonly showHistory = signal(false);
  readonly historyDates = signal<DateHistoryEntry[]>([]);
  readonly historyLoading = signal(false);
  readonly historyGlobal = signal(false);

  readonly filteredOptions = computed(() => {
    const q = this.filter().toLowerCase().trim();
    const opts = this.propertyOptions();
    return q ? opts.filter(p => p.label.toLowerCase().includes(q)) : opts;
  });

  constructor() {
    // Data fetching is handled declaratively via httpResource above
  }

  navigateDate(days: number): void {
    const current = this.operationDate();
    const next = shiftDate(current, days);
    this.operationDate.set(next);
    this.applyFilters();
  }

  goToday(): void {
    this.operationDate.set(todayIso());
    this.applyFilters();
  }

  applyFilters(): void {
    const date = this.operationDate();
    const propId = this.selectedPropId();
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: propId || null, date },
    });
  }

  selectProperty(propId: number, label: string): void {
    this.dropdownOpen.set(false);
    if (propId) this.filter.set(label);
    else this.filter.set('');
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: propId || null, date: this.operationDate() },
    });
  }

  clearProperty(): void {
    this.dropdownOpen.set(false);
    this.filter.set('');
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: null, date: this.operationDate() },
    });
  }

  toggleMenu(): void {
    this.showMenu.update(v => !v);
  }

  closeMenu(): void {
    this.showMenu.set(false);
  }

  openHistory(): void {
    if (this.historyLoading()) return;
    this.closeMenu();
    const propId = this.selectedPropId();
    this.historyGlobal.set(!propId);
    this.showHistory.set(true);
    this.historyLoading.set(true);
    this.errorMessage.set('');
    this.api.getCheckOutDates(propId || undefined).subscribe({
      next: (dates) => {
        this.historyDates.set(dates);
        this.historyLoading.set(false);
      },
      error: () => {
        this.historyLoading.set(false);
        this.errorMessage.set('Error al cargar historial de fechas.');
      }
    });
  }

  closeHistory(): void {
    this.showHistory.set(false);
    this.historyDates.set([]);
    this.errorMessage.set('');
  }

  goToDate(date: string, entryPropId?: number): void {
    this.closeHistory();
    this.operationDate.set(date);
    this.applyFilters();
  }

  toggleDropdown(): void {
    this.dropdownOpen.update(v => !v);
  }

  closeDropdown(): void {
    setTimeout(() => this.dropdownOpen.set(false), 200);
  }

  completeCheckOut(bookingId: string): void {
    const current = this.viewModel();
    if (!current) return;
    this.api.completeCheckOut(bookingId).subscribe({
      next: () => {
        this.message.set('Check-out completado');
        this.errorMessage.set('');
      },
      error: (err: ApiError) => {
        this.errorMessage.set(err.message || 'Error al completar check-out.');
        this.message.set('');
      }
    });
  }

  /** ═══ Review modal ═══ */

  openReviewModal(bookingId: string, propId: number, guestName: string) {
    this.reviewBookingId.set(bookingId);
    this.reviewPropId.set(propId);
    this.reviewGuestName.set(guestName);
    this.reviewRating.set(0);
    this.reviewTitle.set('');
    this.reviewComment.set('');
    this.reviewError.set('');
    this.reviewSuccess.set(false);
    this.showReviewModal.set(true);
  }

  setReviewRating(stars: number) {
    this.reviewRating.set(stars);
  }

  submitReview() {
    if (this.reviewRating() < 1) {
      this.reviewError.set('Selecciona una puntuación de 1 a 5 estrellas.');
      return;
    }
    this.reviewSubmitting.set(true);
    this.reviewError.set('');

    this.http.post(`${this.apiConfig.baseUrl}/reviews/staff`, {
      booking_id: this.reviewBookingId(),
      prop_id: this.reviewPropId(),
      rating: this.reviewRating(),
      title: this.reviewTitle(),
      comment: this.reviewComment(),
    }, { withCredentials: true }).subscribe({
      next: () => {
        this.reviewSuccess.set(true);
        this.reviewSubmitting.set(false);
        setTimeout(() => this.showReviewModal.set(false), 1500);
      },
      error: () => {
        this.reviewError.set('No se pudo guardar la reseña. Intenta nuevamente.');
        this.reviewSubmitting.set(false);
      },
    });
  }

  closeReviewModal() {
    this.showReviewModal.set(false);
  }
}
