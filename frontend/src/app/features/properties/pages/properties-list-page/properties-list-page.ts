import { DecimalPipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

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
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly formBuilder = inject(FormBuilder);

  /** Reactive queryParams bridge — toSignal keeps URL the source of truth. */
  private readonly qp = toSignal(this.route.queryParamMap, {
    initialValue: this.route.snapshot.queryParamMap,
  });

  /** Derived filter — single computed surface that drives both the URL
   *  navigation and the httpResource request below. */
  private readonly queryParams = computed(() => ({
    q: this.qp().get('q') ?? '',
    page: Number(this.qp().get('page') ?? '1') || 1,
  }));

  readonly viewState = computed<ViewState>(() => {
    const v = this.dashboardResource.value();
    if (this.dashboardResource.isLoading() && !v) return 'loading';
    const err = this.dashboardResource.error();
    if (err) return 'error';
    return v ? 'success' : 'loading';
  });

  readonly vm = computed(() => this.dashboardResource.value() ?? null);
  readonly chartView = signal<'daily' | 'weekly'>('weekly');
  readonly todayStr = new Date().toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' });

  readonly form = this.formBuilder.nonNullable.group({
    q: ['']
  });

  /** Side-effect bridge: keep the search `<input>` in sync with the URL's
   *  canonical `q` value. Lives in an effect (not in the httpResource request
   *  function) because Angular docs warn request functions may be called
   *  repeatedly during resource tracking and must remain pure. */
  constructor() {
    effect(() => {
      const { q } = this.queryParams();
      if (this.form.controls.q.value !== q) {
        this.form.controls.q.setValue(q, { emitEvent: false });
      }
    });
  }

  /** httpResource — auto-fetches when q or page changes. Pure request builder. */
  readonly dashboardResource = httpResource<PropertiesDashboardViewModel>(() => {
    const { q, page } = this.queryParams();
    return q ? `/api/management/properties/dashboard?q=${encodeURIComponent(q)}&page=${page}` : `/api/management/properties/dashboard?page=${page}`;
  });

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