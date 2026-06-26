import { CurrencyPipe, DatePipe, SlicePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { toast } from '../../../../core/toast/toast.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { EarningsSummary, EarningsItem, EarningsList } from '../../models/earnings.model';
import { EarningsApiService } from '../../services/earnings-api.service';

@Component({
  selector: 'app-earnings-page',
  imports: [CurrencyPipe, DatePipe, SlicePipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent],
  templateUrl: './earnings-page.html',
  styleUrl: './earnings-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EarningsPageComponent {
  private readonly api = inject(EarningsApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly summaryState = signal<ViewState>('loading');
  readonly listState = signal<ViewState>('loading');
  readonly summary = signal<EarningsSummary | null>(null);
  readonly list = signal<EarningsList | null>(null);
  readonly currentPage = signal(1);

  constructor() {
    this.loadData();
  }

  private loadData() {
    this.summaryState.set('loading');
    this.listState.set('loading');

    this.api.getSummary().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (s) => { this.summary.set(s); this.summaryState.set('success'); },
      error: () => this.summaryState.set('error'),
    });

    this.loadList();
  }

  private loadList() {
    this.listState.set('loading');
    this.api.list(this.currentPage()).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (l) => { this.list.set(l); this.listState.set(l.items.length ? 'success' : 'empty'); },
      error: () => this.listState.set('error'),
    });
  }

  goToPage(page: number) {
    this.currentPage.set(page);
    this.loadList();
  }

  pagesArray(): number[] {
    const total = this.list()?.totalPages ?? 1;
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  markAsPaid(bookingId: string) {
    this.api.markPaid(bookingId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        toast('Comisión marcada como pagada.', 'dark', 4000);
        this.loadData();
      },
      error: (err: ApiError) => {
        toast(err.message || 'Error al marcar comisión como pagada.', 'error', 5000);
      },
    });
  }
}
