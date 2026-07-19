import { DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { PropertiesDashboardViewModel } from '../../models/properties.model';
import { InfoTooltipComponent } from '../../../../shared/ui/info-tooltip/info-tooltip.component';
import { PropertiesApiService } from '../../services/properties-api.service';

@Component({
  selector: 'app-properties-list-page',
  imports: [
    DecimalPipe,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    InfoTooltipComponent,
    ReactiveFormsModule,
    RouterLink
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
  readonly vm = signal<PropertiesDashboardViewModel | null>(null);
  readonly chartView = signal<'daily' | 'weekly'>('weekly');
  readonly todayStr = new Date().toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' });

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
          return this.api.getDashboard(q, page);
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (dashboard) => {
          this.vm.set(dashboard);
          this.viewState.set('success');
        },
        error: () => this.viewState.set('error')
      });
  }

  chartMaxRevenue(): number {
    const chart = this.vm()?.revenueChart;
    if (!chart || chart.length === 0) { return 1; }
    return Math.max(...chart.map(p => p.revenue), 1);
  }

  chartPath(): string {
    const chart = this.vm()?.revenueChart;
    if (!chart || chart.length === 0) { return ''; }
    const maxRev = this.chartMaxRevenue();
    const w = 800 / Math.max(chart.length - 1, 1);
    const points = chart.map((p, i) => ({
      x: i * w,
      y: 200 - (p.revenue / maxRev) * 180
    }));
    return 'M' + points.map(p => `${p.x},${p.y}`).join(' L');
  }

  chartAreaPath(): string {
    const chart = this.vm()?.revenueChart;
    if (!chart || chart.length === 0) { return ''; }
    const maxRev = this.chartMaxRevenue();
    const w = 800 / Math.max(chart.length - 1, 1);
    const points = chart.map((p, i) => ({
      x: i * w,
      y: 200 - (p.revenue / maxRev) * 180
    }));
    const lastX = (chart.length - 1) * w;
    return 'M' + points.map(p => `${p.x},${p.y}`).join(' L') + ` L${lastX},200 L0,200 Z`;
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
      queryParams: { q: currentQuery, page },
      queryParamsHandling: ''
    });
  }

  statusBadgeClass(status: string): string {
    const map: Record<string, string> = {
      'Operational': 'success',
      'Under Review': 'warning',
      'Maintenance': 'danger',
      'pre-paid': 'success',
      'VIP': 'warning',
      'Express': 'success',
      'Standard': 'info',
      'pending': 'warning'
    };
    return map[status] ?? 'info';
  }
}