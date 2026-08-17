import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { DatePipe } from '@angular/common';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { HrApiService } from '../../services/hr-api.service';
import { HorizontalSubNavComponent } from '../../../../shared/ui/horizontal-sub-nav/horizontal-sub-nav';

/** KPI card definitions: id, label, icon, value source key, token color. */
const KPI_CARDS = [
  { id: 'total', label: 'Empleados', icon: 'badge', key: 'totalEmployees' as const, color: 'var(--accent)' },
  { id: 'active', label: 'Activos', icon: 'check_circle', key: 'activeEmployees' as const, color: 'var(--success)' },
  { id: 'inactive', label: 'Inactivos', icon: 'person_off', key: 'inactiveEmployees' as const, color: 'var(--muted-text)' },
  { id: 'departments', label: 'Departamentos', icon: 'groups', key: 'departments' as const, color: 'var(--purple-strong)' },
];

@Component({
  selector: 'app-hr-dashboard-page',
  imports: [DatePipe, ErrorStateComponent, LoadingStateComponent, HorizontalSubNavComponent],
  templateUrl: './hr-dashboard-page.html',
  styleUrl: './hr-dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HrDashboardPageComponent {
  private readonly api = inject(HrApiService);

  // ── Dashboard resource (KPIs globales de RRHH) ──
  private readonly dashboardResource = rxResource({
    params: () => ({}),
    stream: () => this.api.getDashboard(),
  });

  readonly dashboard = computed(() => this.dashboardResource.value() ?? null);

  readonly viewState = computed(() => {
    const r = this.dashboardResource;
    if (r.isLoading() || r.status() === 'idle') return 'loading' as const;
    if (r.error()) return 'error' as const;
    return r.value() ? 'success' as const : 'error' as const;
  });

  readonly errorMessage = computed(() => {
    const err = this.dashboardResource.error();
    return (err as { message?: string } | null)?.message || 'No se pudo cargar el dashboard de RRHH.';
  });

  readonly kpiCards = KPI_CARDS;

  retry() {
    this.dashboardResource.reload();
  }
}
