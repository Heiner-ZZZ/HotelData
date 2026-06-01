import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { PropertiesListViewModel } from '../../models/properties.model';
import { PropertiesApiService } from '../../services/properties-api.service';
import { PropertyListCardComponent } from '../../components/property-list-card/property-list-card';

@Component({
  selector: 'app-properties-list-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    PropertyListCardComponent,
    ReactiveFormsModule
  ],
  templateUrl: './properties-list-page.html',
  styleUrl: './properties-list-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PropertiesListPageComponent {
  private readonly api = inject(PropertiesApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly formBuilder = inject(FormBuilder);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<PropertiesListViewModel | null>(null);

  readonly form = this.formBuilder.nonNullable.group({
    q: ['']
  });

  constructor() {
    this.route.queryParamMap
      .pipe(
        map((params) => ({
          q: params.get('q') ?? '',
          page: Number(params.get('page') ?? '1') || 1
        })),
        distinctUntilChanged((prev, curr) => prev.q === curr.q && prev.page === curr.page),
        switchMap(({ q, page }) => {
          this.form.controls.q.setValue(q, { emitEvent: false });
          this.viewState.set('loading');
          return this.api.getProperties(q, page);
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (vm) => {
          this.viewModel.set(vm);
          this.viewState.set(vm.items.length ? 'success' : 'empty');
        },
        error: () => this.viewState.set('error')
      });
  }

  submit() {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {
        q: this.form.controls.q.value || null,
        page: 1
      },
      queryParamsHandling: ''
    });
  }

  goToPage(page: number) {
    const currentQuery = this.form.controls.q.value || null;
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {
        q: currentQuery,
        page
      },
      queryParamsHandling: ''
    });
  }
}
