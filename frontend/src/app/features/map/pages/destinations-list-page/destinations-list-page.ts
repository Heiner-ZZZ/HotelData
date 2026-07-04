import { SlicePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { Destination, PaginatedDestinations } from '../../models/map.model';
import { MapApiService } from '../../services/map-api.service';

@Component({
  selector: 'app-destinations-list-page',
  imports: [
    EmptyStateComponent, ErrorStateComponent, LoadingStateComponent,
    PageHeaderComponent, RouterLink, ReactiveFormsModule,
  ],
  templateUrl: './destinations-list-page.html',
  styleUrl: './destinations-list-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DestinationsListPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(MapApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);

  readonly viewState = signal<ViewState>('loading');
  readonly data = signal<PaginatedDestinations | null>(null);

  readonly searchForm = this.formBuilder.nonNullable.group({
    search: [''],
  });

  readonly geoFilter = signal<string>('all');

  constructor() {
    this.route.queryParamMap
      .pipe(
        map((params) => ({
          page: Number(params.get('page') ?? '1'),
          search: params.get('search') ?? '',
          hasGeo: params.get('has_geo'),
        })),
        distinctUntilChanged((a, b) =>
          a.page === b.page && a.search === b.search && a.hasGeo === b.hasGeo
        ),
        switchMap(({ page, search, hasGeo }) => {
          this.viewState.set('loading');
          let geoFilter: boolean | undefined;
          if (hasGeo === 'yes') geoFilter = true;
          else if (hasGeo === 'no') geoFilter = false;
          return this.api.getDestinations(page, 50, search || undefined, geoFilter);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (data) => {
          this.data.set(data);
          this.viewState.set(data.items.length ? 'success' : 'empty');
        },
        error: () => this.viewState.set('error'),
      });
  }

  onSearch() {
    const search = this.searchForm.controls.search.value;
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { search: search || null, page: null },
      queryParamsHandling: 'merge',
    });
  }

  setGeoFilter(value: string) {
    this.geoFilter.set(value);
    const map: Record<string, string | null> = { all: null, yes: 'yes', no: 'no' };
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { has_geo: map[value], page: null },
      queryParamsHandling: 'merge',
    });
  }

  goToPage(page: number) {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { page: page > 1 ? page : null },
      queryParamsHandling: 'merge',
    });
  }

  pagesArray(totalPages: number): number[] {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }
}
