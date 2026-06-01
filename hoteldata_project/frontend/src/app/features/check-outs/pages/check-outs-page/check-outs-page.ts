import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { CheckOutsViewModel } from '../../models/check-outs.model';
import { CheckOutsApiService } from '../../services/check-outs-api.service';
import { CheckOutsSummaryCardsComponent } from '../../components/check-outs-summary-cards/check-outs-summary-cards';
import { CheckOutsTableComponent } from '../../components/check-outs-table/check-outs-table';

function todayIso() { return new Date().toISOString().slice(0, 10); }

@Component({
  selector: 'app-check-outs-page',
  imports: [CheckOutsSummaryCardsComponent, CheckOutsTableComponent, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, ReactiveFormsModule],
  templateUrl: './check-outs-page.html',
  styleUrl: './check-outs-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class CheckOutsPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(CheckOutsApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<CheckOutsViewModel | null>(null);
  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly filtersForm = this.formBuilder.nonNullable.group({
    propId: [0],
    operationDate: [todayIso(), [Validators.required]]
  });

  constructor() {
    this.route.queryParamMap.pipe(
      map((params) => ({ propId: Number(params.get('prop_id') ?? '0'), operationDate: params.get('date') || todayIso() })),
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
        this.filtersForm.setValue({ propId: vm.propId ?? 0, operationDate: vm.operationDate }, { emitEvent: false });
        this.viewState.set(vm.items.length ? 'success' : 'empty');
      },
      error: () => this.viewState.set('error')
    });
  }

  applyFilters() {
    const raw = this.filtersForm.getRawValue();
    void this.router.navigate([], { relativeTo: this.route, queryParams: { prop_id: raw.propId || null, date: raw.operationDate } });
  }

  completeCheckOut(bookingId: string) {
    if (!confirm(`Confirmar check-out para ${bookingId}?`)) return;
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
      error: (error: ApiError) => {
        this.errorMessage.set(error.message || 'No fue posible completar el check-out.');
        this.message.set('');
      }
    });
  }
}
