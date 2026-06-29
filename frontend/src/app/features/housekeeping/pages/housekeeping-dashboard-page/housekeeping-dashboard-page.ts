import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin, switchMap } from 'rxjs';

import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { HousekeepingApiService, type HousekeepingDashboard, type DashboardRoomItem } from '../../services/housekeeping-api.service';

interface UpcomingEvent {
  id: string;
  event_type: string;
  room_label: string;
  title?: string;
  task_type: string;
  status: string;
  priority: string;
  scheduled_date?: string;
  created_at: string;
  assigned_to?: string;
  note?: string;
}

interface RoomStatusConfig {
  key: string;
  label: string;
  icon: string;
  color: string;
  bgClass: string;
}

const ROOM_STATUS_CONFIGS: RoomStatusConfig[] = [
  { key: 'available', label: 'Disponible', icon: 'check_circle', color: '#16a34a', bgClass: 'status-available' },
  { key: 'inspected', label: 'Inspeccionada', icon: 'fact_check', color: '#4338ca', bgClass: 'status-inspected' },
  { key: 'clean', label: 'Limpia', icon: 'cleaning_services', color: '#059669', bgClass: 'status-clean' },
  { key: 'occupied', label: 'Ocupada', icon: 'bed', color: '#107a95', bgClass: 'status-occupied' },
  { key: 'cleaning', label: 'Limpieza', icon: 'cleaning_services', color: '#d97706', bgClass: 'status-cleaning' },
  { key: 'dirty', label: 'Sucia', icon: 'report', color: '#92400e', bgClass: 'status-dirty' },
];

const STATUS_COLOR_MAP: Record<string, string> = {
  available: '#16a34a', inspected: '#4338ca', clean: '#059669',
  occupied: '#107a95', cleaning: '#d97706', dirty: '#92400e',
  maintenance: '#ba1a1a', out_of_order: '#ba1a1a', out_of_service: '#6f797d',
};

const STATUS_ICON_MAP: Record<string, string> = {
  available: 'check_circle', inspected: 'fact_check', clean: 'cleaning_services',
  occupied: 'bed', cleaning: 'cleaning_services', dirty: 'report',
  maintenance: 'build', out_of_order: 'dangerous', out_of_service: 'block',
};

const STATUS_LABEL_MAP: Record<string, string> = {
  available: 'Disponible', inspected: 'Inspeccionada', clean: 'Limpia',
  occupied: 'Ocupada', cleaning: 'Limpieza', dirty: 'Sucia',
  maintenance: 'Mantenimiento', out_of_order: 'Fuera Servicio', out_of_service: 'Fuera Servicio',
};

const KPI_CARDS: { key: string; label: string; icon: string; colorToken: string }[] = [
  { key: 'inspected', label: 'Inspeccionada', icon: 'check_circle', colorToken: '#4338ca' },
  { key: 'available', label: 'Vacante Limpia', icon: 'cleaning_services', colorToken: '#107a95' },
  { key: 'dirty', label: 'Vacante Sucia', icon: 'delete_outline', colorToken: '#92400e' },
  { key: 'occupied', label: 'Ocupada Limpia', icon: 'bed', colorToken: '#4a626e' },
  { key: 'cleaning', label: 'En Limpieza', icon: 'cleaning_services', colorToken: '#844910' },
  { key: 'maintenance', label: 'Fuera Servicio', icon: 'build', colorToken: '#ba1a1a' },
];

function extractFloor(roomLabel: string): string {
  const digits = roomLabel.replace(/\D/g, '');
  if (digits.length >= 2) return digits.slice(0, 2);
  if (digits.length === 1) return '0' + digits;
  return '?';
}

@Component({
  selector: 'app-housekeeping-dashboard-page',
  imports: [DatePipe, RouterLink, PropertySelectorComponent, ErrorStateComponent, EmptyStateComponent, LoadingStateComponent, PageHeaderComponent],
  templateUrl: './housekeeping-dashboard-page.html',
  styleUrl: './housekeeping-dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HousekeepingDashboardPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly api = inject(HousekeepingApiService);
  private readonly propertyCtx = inject(PropertyContextService);

  // ── Core state ──

  readonly viewState = signal<ViewState>('loading');
  readonly dashboard = signal<HousekeepingDashboard | null>(null);
  readonly upcomingEvents = signal<UpcomingEvent[]>([]);

  readonly selectedPropId = signal(0);
  readonly selectedLabel = signal('');

  // ── Room map state ──

  readonly selectedRoom = signal<DashboardRoomItem | null>(null);
  readonly floorFilter = signal<string>('all');

  // ── Computed: floors from rooms ──

  readonly floors = computed(() => {
    const rooms = this.dashboard()?.rooms ?? [];
    const floorSet = new Set<string>();
    for (const r of rooms) {
      const f = extractFloor(r.roomLabel);
      if (f !== '?') floorSet.add(f);
    }
    return Array.from(floorSet).sort();
  });

  // ── Computed: filtered rooms for grid ──

  readonly filteredRooms = computed(() => {
    const rooms = this.dashboard()?.rooms ?? [];
    const floor = this.floorFilter();
    if (floor === 'all') return rooms;
    return rooms.filter((r) => extractFloor(r.roomLabel) === floor);
  });

  readonly gridColumns = computed(() => {
    const count = this.filteredRooms().length;
    if (count <= 12) return 4;
    if (count <= 24) return 6;
    return 8;
  });

  // ── Computed: KPI cards ──

  readonly kpiCards = computed(() => {
    const statuses = this.dashboard()?.roomStatuses ?? {};
    // Combine 'out_of_order' and 'out_of_service' into 'maintenance'
    const map: Record<string, number> = {};
    for (const [k, v] of Object.entries(statuses)) {
      if (k === 'out_of_order' || k === 'out_of_service') {
        map['maintenance'] = (map['maintenance'] || 0) + v;
      } else {
        map[k] = (map[k] || 0) + v;
      }
    }

    return KPI_CARDS.map((card) => ({
      ...card,
      count: map[card.key] ?? 0,
      total: this.dashboard()?.totalRooms ?? 0,
    }));
  });

  // ── Computed: room helpers ──

  readonly statusConfigs = ROOM_STATUS_CONFIGS;

  roomStatusColor(status: string): string {
    return STATUS_COLOR_MAP[status] ?? '#6f797d';
  }

  roomStatusIcon(status: string): string {
    return STATUS_ICON_MAP[status] ?? 'help';
  }

  roomStatusLabel(status: string): string {
    return STATUS_LABEL_MAP[status] ?? status;
  }

  isRoomOccupied(status: string): boolean {
    return status === 'occupied' || status === 'cleaning' || status === 'dirty';
  }

  getFloor(roomLabel: string): string {
    return extractFloor(roomLabel);
  }


  // ── Existing computed (cleaning pipeline, etc.) ──

  readonly availableRooms = computed(() => {
    const d = this.dashboard();
    if (!d) return 0;
    return d.totalRooms - d.occupied;
  });

  readonly cleaningCompletionPct = computed(() => {
    const d = this.dashboard();
    if (!d) return 0;
    const total = d.completedToday + d.pendingHousekeepingTasks;
    return total > 0 ? d.completedToday / total : 0;
  });

  readonly maintenanceCompliancePct = computed(() => {
    const d = this.dashboard();
    if (!d) return 0;
    return d.maintenanceCompliancePct ?? 0;
  });

  readonly statusEntries = computed(() => {
    const d = this.dashboard();
    if (!d?.roomStatuses) return [];
    return Object.entries(d.roomStatuses);
  });

  /* ═══ Quick action state ═══ */
  readonly actionLoading = signal<string | null>(null);
  readonly actionMessage = signal('');

  /* ═══ Cleaning Pipeline ═══ */

  readonly pipelineStages = ['dirty', 'cleaning', 'clean', 'inspected', 'available'] as const;

  readonly pipelineLabels: Record<string, string> = {
    dirty: 'Por limpiar', cleaning: 'Limpieza', clean: 'Por inspeccionar',
    inspected: 'Inspeccionada', available: 'Disponible',
  };

  readonly pipelineIcons: Record<string, string> = {
    dirty: 'report', cleaning: 'cleaning_services', clean: 'check',
    inspected: 'fact_check', available: 'check_circle',
  };

  readonly pipelineColors: Record<string, string> = {
    dirty: '#92400e', cleaning: '#d97706', clean: '#059669',
    inspected: '#4338ca', available: '#16a34a',
  };

  readonly cleaningFlowData = computed(() => {
    const d = this.dashboard();
    if (!d?.roomStatuses) return [];
    const rs = d.roomStatuses;
    const totalInPipeline = this.pipelineStages.reduce((sum, s) => sum + (rs[s] || 0), 0);
    return this.pipelineStages.map((stage) => ({
      key: stage,
      count: rs[stage] || 0,
      label: this.pipelineLabels[stage],
      icon: this.pipelineIcons[stage],
      color: this.pipelineColors[stage],
      pct: totalInPipeline > 0 ? Math.round(((rs[stage] || 0) / totalInPipeline) * 100) : 0,
    }));
  });

  readonly selectedRoomStatusLabel = computed(() => {
    const room = this.selectedRoom();
    if (!room) return '';
    return this.roomStatusLabel(room.status);
  });

  constructor() {
    this.route.queryParamMap
      .pipe(
        switchMap((params) => {
          const propId = Number(params.get('prop_id') ?? '0');
          const label = params.get('prop_label') ?? '';
          this.selectedPropId.set(propId);
          this.selectedLabel.set(label);
          if (!propId) {
            this.viewState.set('empty');
            this.dashboard.set(null);
            this.upcomingEvents.set([]);
            this.propertyCtx.clear();
            return [];
          }
          this.viewState.set('loading');
          this.propertyCtx.setProperty(propId, label || `Propiedad #${propId}`);
          return forkJoin({
            dashboard: this.api.getDashboard(propId),
            events: this.api.getUpcomingEvents(propId),
          });
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: ({ dashboard, events }) => {
          if (dashboard) {
            this.dashboard.set(dashboard);
            this.viewState.set('success');
          }
          if (events) {
            this.upcomingEvents.set(events);
          }
        },
        error: () => this.viewState.set('error'),
      });
  }

  // ── Room selection ──

  selectRoom(room: DashboardRoomItem): void {
    this.selectedRoom.set(
      this.selectedRoom()?.id === room.id ? null : room
    );
  }

  setFloor(floor: string): void {
    this.floorFilter.set(floor);
    this.selectedRoom.set(null);
  }

  // ── Quick actions (existing, preserved) ──

  private refreshDashboard(): void {
    const propId = this.selectedPropId();
    if (!propId) return;
    this.api.getDashboard(propId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (dashboard) => {
        this.dashboard.set(dashboard);
        this.selectedRoom.set(null);
      },
    });
  }

  startCleaning(): void {
    const propId = this.selectedPropId();
    const dashboard = this.dashboard();
    if (!propId || !dashboard) return;
    const dirtyCount = dashboard.roomStatuses?.dirty || 0;
    if (dirtyCount === 0) return;

    this.actionLoading.set('cleaning');
    this.actionMessage.set('');

    this.api.getRoomStatus(propId, 'dirty', 1).pipe(
      switchMap((res) => {
        const roomLabels = res.items.map((r) => r.roomLabel);
        if (roomLabels.length === 0) {
          this.actionLoading.set(null);
          this.refreshDashboard();
          return [];
        }
        return this.api.bulkUpdateRoomStatus(propId, roomLabels, 'cleaning', 'Marcado desde dashboard');
      }),
      switchMap(() => {
        this.actionMessage.set('Habitaciones marcadas como \'En limpieza\'');
        this.actionLoading.set(null);
        this.refreshDashboard();
        return [];
      }),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      error: () => {
        this.actionLoading.set(null);
        this.actionMessage.set('Error al actualizar estado');
      },
    });
  }

  advanceToInspected(): void {
    const propId = this.selectedPropId();
    const dashboard = this.dashboard();
    if (!propId || !dashboard) return;
    const cleanCount = dashboard.roomStatuses?.clean || 0;
    if (cleanCount === 0) return;

    this.actionLoading.set('inspected');
    this.actionMessage.set('');

    this.api.getRoomStatus(propId, 'clean', 1).pipe(
      switchMap((res) => {
        const roomLabels = res.items.map((r) => r.roomLabel);
        if (roomLabels.length === 0) {
          this.actionLoading.set(null);
          this.refreshDashboard();
          return [];
        }
        return this.api.bulkUpdateRoomStatus(propId, roomLabels, 'inspected', 'Marcado desde dashboard');
      }),
      switchMap(() => {
        this.actionMessage.set('Habitaciones marcadas como \'Inspeccionadas\'');
        this.actionLoading.set(null);
        this.refreshDashboard();
        return [];
      }),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      error: () => {
        this.actionLoading.set(null);
        this.actionMessage.set('Error al actualizar estado');
      },
    });
  }

  advanceToAvailable(): void {
    const propId = this.selectedPropId();
    const dashboard = this.dashboard();
    if (!propId || !dashboard) return;
    const inspectedCount = dashboard.roomStatuses?.inspected || 0;
    if (inspectedCount === 0) return;

    this.actionLoading.set('available');
    this.actionMessage.set('');

    this.api.getRoomStatus(propId, 'inspected', 1).pipe(
      switchMap((res) => {
        const roomLabels = res.items.map((r) => r.roomLabel);
        if (roomLabels.length === 0) {
          this.actionLoading.set(null);
          this.refreshDashboard();
          return [];
        }
        return this.api.bulkUpdateRoomStatus(propId, roomLabels, 'available', 'Liberado desde dashboard');
      }),
      switchMap(() => {
        this.actionMessage.set('Habitaciones marcadas como \'Disponibles\'');
        this.actionLoading.set(null);
        this.refreshDashboard();
        return [];
      }),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      error: () => {
        this.actionLoading.set(null);
        this.actionMessage.set('Error al actualizar estado');
      },
    });
  }

  onPropSelected(event: { propId: number; label: string }): void {
    const label = event.label || `Propiedad #${event.propId}`;
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null, prop_label: label || null },
    });
  }
}
