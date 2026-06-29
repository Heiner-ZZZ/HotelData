import { SlicePipe } from '@angular/common';
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
import { HousekeepingApiService, type HousekeepingDashboard } from '../../services/housekeeping-api.service';

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

@Component({
  selector: 'app-housekeeping-dashboard-page',
  imports: [SlicePipe, RouterLink, PropertySelectorComponent, ErrorStateComponent, EmptyStateComponent, LoadingStateComponent, PageHeaderComponent],
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

  readonly viewState = signal<ViewState>('loading');
  readonly dashboard = signal<HousekeepingDashboard | null>(null);
  readonly upcomingEvents = signal<UpcomingEvent[]>([]);

  readonly selectedPropId = signal(0);
  readonly selectedLabel = signal('');

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

  readonly occupancyCircumference = computed(() => {
    const r = 54;
    return 2 * Math.PI * r;
  });

  readonly occupancyOffset = computed(() => {
    const d = this.dashboard();
    if (!d) return 0;
    const circ = this.occupancyCircumference();
    return circ - (d.occupancyRate / 100) * circ;
  });

  readonly statusEntries = computed(() => {
    const d = this.dashboard();
    if (!d?.roomStatuses) return [];
    return Object.entries(d.roomStatuses);
  });

  /* ═══ Quick action state ═══ */
  readonly actionLoading = signal<string | null>(null);  // 'dirty' | 'cleaning' | 'clean' | 'inspected'
  readonly actionMessage = signal('');

  /* ═══ Cleaning Pipeline ═══ */

  readonly pipelineStages = ['dirty', 'cleaning', 'clean', 'inspected', 'available'] as const;

  readonly pipelineLabels: Record<string, string> = {
    dirty: 'Por limpiar',
    cleaning: 'Limpieza',
    clean: 'Por inspeccionar',
    inspected: 'Inspeccionada',
    available: 'Disponible',
  };

  readonly pipelineIcons: Record<string, string> = {
    dirty: 'report',
    cleaning: 'cleaning_services',
    clean: 'check',
    inspected: 'fact_check',
    available: 'check_circle',
  };

  readonly pipelineColors: Record<string, string> = {
    dirty: '#92400e',
    cleaning: '#d97706',
    clean: '#059669',
    inspected: '#4338ca',
    available: '#16a34a',
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

  /** Refresh dashboard data after a quick action. */
  private refreshDashboard(): void {
    const propId = this.selectedPropId();
    if (!propId) return;
    this.api.getDashboard(propId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (dashboard) => this.dashboard.set(dashboard),
    });
  }

  /** Quick action: move all dirty rooms → cleaning (bulk status + create tasks). */
  startCleaning(): void {
    const propId = this.selectedPropId();
    const dashboard = this.dashboard();
    if (!propId || !dashboard) return;
    const dirtyCount = dashboard.roomStatuses?.dirty || 0;
    if (dirtyCount === 0) return;

    this.actionLoading.set('cleaning');
    this.actionMessage.set('');

    // 1. Fetch dirty room labels to update
    this.api.getRoomStatus(propId, 'dirty', 1).pipe(
      switchMap((res) => {
        const roomLabels = res.items.map((r) => r.roomLabel);
        if (roomLabels.length === 0) {
          this.actionLoading.set(null);
          this.refreshDashboard();
          return [];
        }
        // 2. Bulk update status to 'cleaning'
        return this.api.bulkUpdateRoomStatus(propId, roomLabels, 'cleaning', 'Marcado desde dashboard');
      }),
      switchMap(() => {
        // 3. Create cleaning tasks for each dirty room (via tasks list refresh)
        //    The status update auto-creates tasks through the check-out flow,
        //    but here we just update status — tasks will be manually assigned.
        this.actionMessage.set(`Habitaciones marcadas como 'En limpieza'`);
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

  /** Quick action: advance clean → inspected via bulk status update. */
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
        this.actionMessage.set(`Habitaciones marcadas como 'Inspeccionadas'`);
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

  /** Quick action: advance inspected → available via bulk status update. */
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
        this.actionMessage.set(`Habitaciones marcadas como 'Disponibles'`);
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