import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { API_CONFIG } from '../../../../core/api/api.config';

import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { CheckOutsViewModel } from '../../models/check-outs.model';
import { CheckOutsApiService, type DateHistoryEntry } from '../../services/check-outs-api.service';

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
  imports: [DatePipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, ReactiveFormsModule, FormsModule],
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
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<CheckOutsViewModel | null>(null);
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

  readonly dateForm = this.formBuilder.nonNullable.group({
    operationDate: [todayIso(), [Validators.required]]
  });

  readonly selectedPropId = signal(0);
  readonly selectedPropName = signal('');
  readonly filter = signal('');
  readonly propertyOptions = signal<Array<{ propId: number; label: string }>>([]);
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
    this.route.queryParamMap.pipe(
      map((params) => ({
        propId: Number(params.get('prop_id') ?? '0'),
        operationDate: params.get('date') || todayIso()
      })),
      distinctUntilChanged((a, b) => a.propId === b.propId && a.operationDate === b.operationDate),
      switchMap(({ propId, operationDate }) => {
        this.viewState.set('loading');
        this.message.set('');
        this.errorMessage.set('');
        return this.api.getCheckOuts(operationDate, propId || undefined);
      }),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (vm) => {
        this.viewModel.set(vm);
        this.dateForm.controls.operationDate.setValue(vm.operationDate, { emitEvent: false });
        this.propertyOptions.set(vm.propertyOptions);
        const selected = vm.propertyOptions.find(p => p.propId === vm.propId);
        this.selectedPropId.set(vm.propId ?? 0);
        this.selectedPropName.set(selected?.label || '');
        this.viewState.set(vm.items.length ? 'success' : 'empty');
      },
      error: () => this.viewState.set('error')
    });
  }

  navigateDate(days: number): void {
    const current = this.dateForm.controls.operationDate.value;
    this.dateForm.controls.operationDate.setValue(shiftDate(current, days));
    this.applyFilters();
  }

  goToday(): void {
    this.dateForm.controls.operationDate.setValue(todayIso());
    this.applyFilters();
  }

  applyFilters(): void {
    const date = this.dateForm.controls.operationDate.value;
    const propId = this.selectedPropId();
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: propId || null, date }
    });
  }

  selectProperty(propId: number, label: string): void {
    this.dropdownOpen.set(false);
    this.selectedPropId.set(propId);
    this.selectedPropName.set(label);
    if (propId) this.filter.set(label);
    else this.filter.set('');
    this.applyFilters();
  }

  clearProperty(): void {
    this.selectProperty(0, '');
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
    this.api.getCheckOutDates(propId || undefined).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
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
    if (entryPropId) {
      const opt = this.propertyOptions().find(p => p.propId === entryPropId);
      if (opt) {
        this.selectedPropId.set(entryPropId);
        this.selectedPropName.set(opt.label);
      }
    }
    this.dateForm.controls.operationDate.setValue(date);
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
    this.api.completeCheckOut(bookingId).pipe(
      switchMap(() => this.api.getCheckOuts(current.operationDate, current.propId || undefined)),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (vm) => {
        this.viewModel.set(vm);
        this.viewState.set(vm.items.length ? 'success' : 'empty');
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
