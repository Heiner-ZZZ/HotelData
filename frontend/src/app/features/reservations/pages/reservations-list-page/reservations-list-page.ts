import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ReservationsListViewModel } from '../../models/reservations.model';
import { ReservationsApiService, type DateHistoryEntry } from '../../services/reservations-api.service';

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
  selector: 'app-reservations-list-page',
  imports: [DatePipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, ReactiveFormsModule, RouterLink],
  templateUrl: './reservations-list-page.html',
  styleUrl: './reservations-list-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ReservationsListPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly reservationsApi = inject(ReservationsApiService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<ReservationsListViewModel | null>(null);

  readonly dateForm = this.formBuilder.nonNullable.group({
    createdDate: ['', [Validators.required]]
  });

  // Current date filter (to sync between switchMap and next)
  readonly currentDateFilter = signal('');

  // More menu (⋮)
  readonly showMenu = signal(false);

  // Date history
  readonly showHistory = signal(false);
  readonly historyDates = signal<DateHistoryEntry[]>([]);
  readonly historyLoading = signal(false);

  constructor() {
    this.activatedRoute.queryParamMap
      .pipe(
        map((params) => ({
          page: Number(params.get('page') ?? '1'),
          createdDate: params.get('date') || ''
        })),
        distinctUntilChanged((a, b) => a.page === b.page && a.createdDate === b.createdDate),
        switchMap(({ page, createdDate }) => {
          this.viewState.set('loading');
          this.currentDateFilter.set(createdDate || '');
          return this.reservationsApi.getReservations(page, createdDate || undefined);
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (data) => {
          this.data.set(data);
          this.dateForm.controls.createdDate.setValue(this.currentDateFilter(), { emitEvent: false });
          this.viewState.set(data.items.length ? 'success' : 'empty');
        },
        error: () => this.viewState.set('error')
      });
  }

  navigateDate(days: number): void {
    const current = this.dateForm.controls.createdDate.value || todayIso();
    this.dateForm.controls.createdDate.setValue(shiftDate(current, days));
    this.applyFilter();
  }

  goToday(): void {
    this.dateForm.controls.createdDate.setValue(todayIso());
    this.applyFilter();
  }

  clearDateFilter(): void {
    this.dateForm.controls.createdDate.setValue('');
    this.applyFilter();
  }

  applyFilter(): void {
    const createdDate = this.dateForm.controls.createdDate.value;
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { date: createdDate || null, page: null }
    });
  }

  goToPage(page: number) {
    const createdDate = this.dateForm.controls.createdDate.value;
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { date: createdDate || null, page: page > 1 ? page : null }
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
    this.showHistory.set(true);
    this.historyLoading.set(true);
    this.reservationsApi.getReservationDates().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (dates) => {
        this.historyDates.set(dates);
        this.historyLoading.set(false);
      },
      error: () => {
        this.historyLoading.set(false);
      }
    });
  }

  closeHistory(): void {
    this.showHistory.set(false);
    this.historyDates.set([]);
  }

  goToDate(date: string): void {
    this.closeHistory();
    this.dateForm.controls.createdDate.setValue(date);
    this.applyFilter();
  }
}
