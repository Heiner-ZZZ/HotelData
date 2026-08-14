import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, effect, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { PropertiesDashboardViewModel } from '../../models/properties.model';
import type { PropertiesDashboardResponseDto } from '../../models/properties.dto';
import { mapPropertiesDashboardResponse } from '../../mappers/properties.mapper';
import { InfoTooltipComponent } from '../../../../shared/ui/info-tooltip/info-tooltip.component';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { PropertiesApiService } from '../../services/properties-api.service';

@Component({
  selector: 'app-properties-list-page',
  imports: [
    EmptyStateComponent,
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
  private readonly propertyCtx = inject(PropertyContextService);

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

    // Gerente con UN solo hotel asignado: la lista no aporta — ir directo a la
    // propiedad. La lista solo tiene sentido con 2+ hoteles (o roles sin filtro).
    effect(() => {
      if (!this.propertyCtx.ready()) return;
      if (!this.propertyCtx.singleHotelMode()) return;
      const propId = this.propertyCtx.defaultPropId();
      if (propId > 0) {
        void this.router.navigate(['/management/properties', propId], { replaceUrl: true });
      }
    });
  }

  /** httpResource — auto-fetches when q or page changes. Pure request builder. */
  readonly dashboardResource = httpResource<PropertiesDashboardViewModel>(() => {
    const { q, page } = this.queryParams();
    return q ? `/api/management/properties/dashboard?q=${encodeURIComponent(q)}&page=${page}` : `/api/management/properties/dashboard?page=${page}`;
  }, {
    parse: (dto) => mapPropertiesDashboardResponse(dto as PropertiesDashboardResponseDto),
  });

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