import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { HousekeepingApiService, type HousekeepingDashboard } from '../../services/housekeeping-api.service';

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

const STATUS_COLORS: Record<string, string> = {
  vacant_dirty: '#92400e',
  vacant_clean: '#16a34a',
  occupied_clean: '#006076',
  occupied_dirty: '#d97706',
  cleaning_in_progress: '#ca8a04',
  cleaning_completed: '#059669',
  inspected: '#4338ca',
  out_of_service: '#6f797d',
  out_of_order: '#ba1a1a',
  maintenance_requested: '#ea580c',
};

/** KPI card definitions: id, label, icon, value source key */
const KPI_CARDS = [
  { id: 'occupied', label: 'Ocupadas', icon: 'bed', key: 'occupied' as const, color: '#006076' },
  { id: 'vacant_clean', label: 'Vacantes Limpias', icon: 'check_circle', key: 'clean_rooms' as const, color: '#16a34a' },
  { id: 'pending', label: 'Pendientes', icon: 'report', key: 'pending_rooms' as const, color: '#92400e' },
  { id: 'cleaning', label: 'En Limpieza', icon: 'cleaning_services', key: 'in_cleaning' as const, color: '#ca8a04' },
  { id: 'inspected', label: 'Inspección', icon: 'fact_check', key: 'inspected' as const, color: '#4338ca' },
  { id: 'maintenance', label: 'Mantenimiento', icon: 'build', key: 'maintenance_requested' as const, color: '#ea580c' },
  { id: 'oos', label: 'F/Servicio', icon: 'block', key: 'out_of_service' as const, color: '#6f797d' },
  { id: 'ooo', label: 'F/Orden', icon: 'dangerous', key: 'out_of_order' as const, color: '#ba1a1a' },
];

@Component({
  selector: 'app-housekeeping-dashboard-page',
  imports: [DatePipe, FormsModule, ErrorStateComponent, LoadingStateComponent, PropertySelectorComponent],
  templateUrl: './housekeeping-dashboard-page.html',
  styleUrl: './housekeeping-dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HousekeepingDashboardPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(HousekeepingApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly propertyCtx = inject(PropertyContextService);

  readonly viewState = signal<ViewState>('loading');
  readonly dashboard = signal<HousekeepingDashboard | null>(null);
  readonly selectedPropId = signal(0);
  readonly selectedFloor = signal<string>('');

  readonly kpiCards = KPI_CARDS;

  constructor() {
    this.route.queryParamMap
      .pipe(
        map((params) => ({
          propId: Number(params.get('prop_id') ?? '0'),
          propLabel: params.get('prop_label') ?? '',
        })),
        distinctUntilChanged((a, b) => a.propId === b.propId),
        switchMap(({ propId, propLabel }) => {
          this.viewState.set('loading');
          this.selectedPropId.set(propId);
          this.selectedFloor.set('');
          if (!propId) {
            this.propertyCtx.clear();
            return this.api.getDashboard();
          }
          this.propertyCtx.setProperty(propId, propLabel || `Propiedad #${propId}`);
          return this.api.getDashboard(propId);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (data) => {
          this.dashboard.set(data);
          this.viewState.set('success');
        },
        error: () => this.viewState.set('error'),
      });
  }

  /** KPI value from the dashboard object. */
  kpiValue(key: string): number {
    const d = this.dashboard();
    if (!d) return 0;
    return (d as any)[key] ?? 0;
  }

  /** Total rooms for occupancy rate display. */
  readonly totalRooms = computed(() => this.dashboard()?.totalRooms ?? 0);
  readonly occupancyRate = computed(() => this.dashboard()?.occupancyRate ?? 0);
  readonly completedToday = computed(() => this.dashboard()?.completedToday ?? 0);
  readonly pendingTasks = computed(() => this.dashboard()?.pendingHousekeepingTasks ?? 0);
  readonly floors = computed(() => this.dashboard()?.floors ?? []);
  readonly filteredFloors = computed(() => {
    const fl = this.floors();
    const sf = this.selectedFloor();
    if (!sf) return fl;
    return fl.filter((f) => f.floor === sf);
  });

  getStatusColor(status: string): string {
    return STATUS_COLORS[status] ?? '#6f797d';
  }

  getStatusLabel(status: string): string {
    return STATUS_LABELS[status] ?? status;
  }

  /** Convert floor status_counts to sorted entries for template display. */
  _floorCounts(counts: Record<string, number>): Array<[string, number]> {
    return Object.entries(counts).filter(([, v]) => v > 0);
  }

  onPropSelected(event: { propId: number; label: string }): void {
    const label = event.label || `Propiedad #${event.propId}`;
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null, prop_label: label || null },
    });
  }
}
