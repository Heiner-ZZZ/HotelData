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

  onPropSelected(event: { propId: number; label: string }): void {
    const label = event.label || `Propiedad #${event.propId}`;
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null, prop_label: label || null },
    });
  }
}