import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ManualReservationListItem } from '../../models/manual-reservation.model';
import { ManualReservationApiService } from '../../services/manual-reservation-api.service';

@Component({
  selector: 'app-manual-reservations-list-page',
  imports: [CurrencyPipe, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, RouterLink],
  templateUrl: './manual-reservations-list-page.html',
  styleUrl: './manual-reservations-list-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ManualReservationsListPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);
  private readonly api = inject(ManualReservationApiService);

  readonly viewState = signal<ViewState>('loading');
  readonly items = signal<ManualReservationListItem[]>([]);
  readonly total = signal(0);
  readonly page = signal(1);
  readonly hasNext = signal(false);
  readonly hasPrev = signal(false);

  constructor() {
    this.activatedRoute.queryParamMap
      .pipe(
        map((params) => Number(params.get('page') ?? '1')),
        distinctUntilChanged(),
        switchMap((page) => {
          this.viewState.set('loading');
          return this.api.getManualReservations(page);
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (data) => {
          this.items.set(data.items);
          this.total.set(data.total);
          this.page.set(data.page);
          this.hasNext.set(data.hasNext);
          this.hasPrev.set(data.hasPrev);
          this.viewState.set(data.items.length ? 'success' : 'empty');
        },
        error: () => this.viewState.set('error')
      });
  }

  goToPage(page: number) {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { page: page > 1 ? page : null }
    });
  }
}
