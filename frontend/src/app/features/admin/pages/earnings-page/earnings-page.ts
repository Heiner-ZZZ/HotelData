import { CurrencyPipe, DatePipe, SlicePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { ToastService } from '../../../../shared/services/toast.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { EarningsSummary, EarningsList } from '../../models/earnings.model';
import type { EarningsSummaryDto, EarningsListDto } from '../../models/earnings.dto';
import { EarningsApiService } from '../../services/earnings-api.service';
import { mapSummary, mapList } from '../../mappers/earnings.mapper';

@Component({
  selector: 'app-earnings-page',
  imports: [CurrencyPipe, DatePipe, SlicePipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent],
  templateUrl: './earnings-page.html',
  styleUrl: './earnings-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EarningsPageComponent {
  private readonly api = inject(EarningsApiService);
  private readonly toast = inject(ToastService);
  private readonly destroyRef = inject(DestroyRef);

  readonly currentPage = signal(1);

  readonly summaryResource = httpResource<EarningsSummary>(
    () => `/api/management/products/earnings/summary`,
    { parse: (dto) => mapSummary(dto as EarningsSummaryDto) },
  );

  readonly listResource = httpResource<EarningsList>(
    () => `/api/management/products/earnings?page=${this.currentPage()}&page_size=20`,
    { parse: (dto) => mapList(dto as EarningsListDto) },
  );

  readonly summary = computed(() => this.summaryResource.value());
  readonly list = computed(() => this.listResource.value());

  readonly summaryState = computed(() => {
    if (this.summaryResource.error()) return 'error' as const;
    if (this.summaryResource.isLoading()) return 'loading' as const;
    return 'success' as const;
  });

  readonly listState = computed(() => {
    if (this.listResource.error()) return 'error' as const;
    if (this.listResource.isLoading()) return 'loading' as const;
    const l = this.list();
    return l && l.items.length ? ('success' as const) : ('empty' as const);
  });



  pagesArray(): number[] {
    const total = this.list()?.totalPages ?? 1;
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  goToPage(page: number) {
    this.currentPage.set(page);
  }

  markAsPaid(bookingId: string) {
    this.api.markPaid(bookingId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.toast.show('Comisión marcada como pagada.', 'info', 4000);
        this.summaryResource.reload();
        this.listResource.reload();
      },
      error: (err: ApiError) => {
        this.toast.show(err.message || 'Error al marcar comisión como pagada.', 'error', 5000);
      },
    });
  }
}
