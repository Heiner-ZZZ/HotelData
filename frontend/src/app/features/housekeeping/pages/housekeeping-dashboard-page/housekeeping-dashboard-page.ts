import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { EMPTY } from 'rxjs';


import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { HousekeepingApiService } from '../../services/housekeeping-api.service';
import { HorizontalSubNavComponent } from '../../../../shared/ui/horizontal-sub-nav/horizontal-sub-nav';
import { statusColor } from '../../../../shared/utils/semantic-color.helper';

const STATUS_LABELS: Record<string, string> = {
  vacant_dirty: 'Vacante Sucia',
  vacant_clean: 'Vacante Limpia',
  occupied_clean: 'Ocupada Limpia',
  occupied_dirty: 'Ocupada Sucia',
  cleaning_in_progress: 'Limpieza en Progreso',
  cleaning_completed: 'Limpieza Completada',
  inspected: 'Inspeccionada',
  out_of_service: 'Fuera de Servicio',
  out_of_order: 'Fuera de Orden',
  maintenance_requested: 'Mtto Solicitado',
};

/**
 * Status colors — delegated to design tokens
 * (`frontend/src/styles/_scss-variables.scss`). Status keys kept
 * verbatim so the existing template lookups work; only the value
 * shifts from a hardcoded hex to `var(--token)`. Auto-adapts to
 * light/dark theme via the cascade.
 */
const STATUS_COLORS: Record<string, string> = {
  vacant_dirty: 'var(--warning-strong)',
  vacant_clean: 'var(--success)',
  occupied_clean: 'var(--accent)',
  occupied_dirty: 'var(--warning)',
  cleaning_in_progress: 'var(--cyan)',
  cleaning_completed: 'var(--success-strong)',
  inspected: 'var(--purple-strong)',
  out_of_service: 'var(--muted-text)',
  out_of_order: 'var(--danger)',
  maintenance_requested: 'var(--warning)',
};

/** KPI card definitions: id, label, icon, value source key. The
 *  `color` field is a `var(--token)` consumer; the cascade handles
 *  light/dark theme switching. */
const KPI_CARDS = [
  { id: 'occupied', label: 'Ocupadas', icon: 'bed', key: 'occupied' as const, color: 'var(--accent)' },
  { id: 'vacant_clean', label: 'Vacantes Limpias', icon: 'check_circle', key: 'clean_rooms' as const, color: 'var(--success)' },
  { id: 'pending', label: 'Pendientes', icon: 'report', key: 'pending_rooms' as const, color: 'var(--warning-strong)' },
  { id: 'cleaning', label: 'En Limpieza', icon: 'cleaning_services', key: 'in_cleaning' as const, color: 'var(--cyan)' },
  { id: 'inspected', label: 'Inspección', icon: 'fact_check', key: 'inspected' as const, color: 'var(--purple-strong)' },
  { id: 'maintenance', label: 'Mantenimiento', icon: 'build', key: 'maintenance_requested' as const, color: 'var(--warning)' },
  { id: 'oos', label: 'F/Servicio', icon: 'block', key: 'out_of_service' as const, color: 'var(--muted-text)' },
  { id: 'ooo', label: 'F/Orden', icon: 'dangerous', key: 'out_of_order' as const, color: 'var(--danger)' },
];

@Component({
  selector: 'app-housekeeping-dashboard-page',
  imports: [FormsModule, ErrorStateComponent, LoadingStateComponent, PropertySelectorComponent, HorizontalSubNavComponent],
  templateUrl: './housekeeping-dashboard-page.html',
  styleUrl: './housekeeping-dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HousekeepingDashboardPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(HousekeepingApiService);
  private readonly propertyCtx = inject(PropertyContextService);

  // ── Reactive URL params ──
  private readonly qp = toSignal(this.route.queryParamMap, { initialValue: this.route.snapshot.queryParamMap });

  readonly selectedPropId = computed(() => Number(this.qp()?.get('prop_id') ?? '0'));
  private readonly selectedLabel = computed(() => this.qp()?.get('prop_label') ?? '');
  readonly selectedFloor = computed(() => this.qp()?.get('floor') ?? '');

  // ── Dashboard resource ──
  private readonly dashboardResource = rxResource<any, any>({
    params: () => {
      const pid = this.selectedPropId();
      return { propId: pid };
    },
    stream: ({ params }) => {
      const { propId } = params as any;
      if (propId) {
        this.propertyCtx.setProperty(propId, this.selectedLabel() || `Propiedad #${propId}`);
        return this.api.getDashboard(propId);
      }
      // Sin prop_id el backend responde 400 (require_prop_permission). No
      // disparar la petición: dejar el recurso idle y mostrar el bloque
      // "Selecciona una propiedad" (sin error de prop_id).
      this.propertyCtx.clear();
      return EMPTY;
    },
  });

  readonly dashboard = computed(() => this.dashboardResource.value() ?? null);

  readonly viewState = computed(() => {
    // Sin hotel seleccionado: caer al @default (bloque "Selecciona una
    // propiedad") en vez de disparar una petición que el backend responde
    // con 400 por falta de prop_id.
    if (!this.selectedPropId()) return 'success' as const;
    const r = this.dashboardResource;
    if (r.isLoading() || r.status() === 'idle') return 'loading' as const;
    if (r.error()) return 'error' as const;
    const d = r.value();
    if (!d) return 'error' as const;
    return 'success' as const;
  });

  readonly kpiCards = KPI_CARDS;

  // ── Derived KPIs ──
  readonly totalRooms = computed(() => this.dashboard()?.totalRooms ?? 0);
  readonly occupancyRate = computed(() => this.dashboard()?.occupancyRate ?? 0);
  readonly completedToday = computed(() => this.dashboard()?.completedToday ?? 0);
  readonly pendingTasks = computed(() => this.dashboard()?.pendingHousekeepingTasks ?? 0);
  readonly floors = computed(() => this.dashboard()?.floors ?? []);
  readonly filteredFloors = computed(() => {
    const fl = this.floors();
    const sf = this.selectedFloor();
    if (!sf) return fl;
    return fl.filter((f: any) => f.floor === sf);
  });

  // ── Helpers ──

  /** KPI value from the dashboard object. */
  kpiValue(key: string): number {
    const d = this.dashboard();
    if (!d) return 0;
    return (d as any)[key] ?? 0;
  }

  getStatusColor(status: string): string {
    return STATUS_COLORS[status] ?? statusColor(null);
  }

  getStatusLabel(status: string): string {
    return STATUS_LABELS[status] ?? status;
  }

  /** Convert floor status_counts to sorted entries for template display. */
  _floorCounts(counts: Record<string, number>): [string, number][] {
    return Object.entries(counts).filter(([, v]) => v > 0);
  }

  // ── Navigation ──

  onPropSelected(event: { propId: number; label: string }): void {
    const label = event.label || `Propiedad #${event.propId}`;
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null, prop_label: label || null, floor: null },
    });
  }

  onFloorSelected(floor: string): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { floor: floor || null },
      queryParamsHandling: 'merge',
    });
  }
}
