import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { toSignal } from '@angular/core/rxjs-interop';
import { httpResource } from '@angular/common/http';
import { ActivatedRoute, Router } from '@angular/router';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { HousekeepingSubNavComponent } from '../../components/housekeeping-sub-nav/housekeeping-sub-nav';
import { HousekeepingApiService, type HousekeepingOperationsAnalytics } from '../../services/housekeeping-api.service';

@Component({
  selector: 'app-housekeeping-operations-page',
  imports: [DecimalPipe, PropertySelectorComponent, HousekeepingSubNavComponent],
  templateUrl: './housekeeping-operations-page.html',
  styleUrl: './housekeeping-operations-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HousekeepingOperationsPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(HousekeepingApiService);
  private readonly propertyContext = inject(PropertyContextService);
  private readonly queryParams = toSignal(this.route.queryParamMap, { initialValue: this.route.snapshot.queryParamMap });

  readonly selectedPropId = computed(() => Number(this.queryParams().get('prop_id') ?? '0'));
  readonly selectedLabel = computed(() => this.queryParams().get('prop_label') ?? '');
  readonly dateFrom = signal('');
  readonly dateTo = signal('');

  readonly operationsResource = httpResource<HousekeepingOperationsAnalytics>(() => {
    const propId = this.selectedPropId();
    if (!propId) return undefined;
    const params = new URLSearchParams({ days: '30' });
    params.set('prop_id', String(propId));
    if (this.dateFrom()) params.set('date_from', this.dateFrom());
    if (this.dateTo()) params.set('date_to', this.dateTo());
    return `/api/housekeeping/operations/analytics?${params.toString()}`;
  });

  readonly data = computed(() => this.operationsResource.value() ?? null);
  readonly summary = computed(() => this.data()?.summary ?? null);
  readonly rows = computed(() => this.data()?.rows ?? []);

  constructor() {
    effect(() => {
      const id = this.selectedPropId();
      const label = this.selectedLabel();
      if (id) this.propertyContext.setProperty(id, label || `Propiedad #${id}`);
    });
  }

  onPropSelected(event: { propId: number; label: string }): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null, prop_label: event.label || null },
      queryParamsHandling: 'merge',
    });
  }

  reload(): void { this.operationsResource.reload(); }

  formatMinutes(value: number | null | undefined): string {
    if (value == null) return 'Sin datos';
    if (value < 60) return `${Math.round(value)} min`;
    return `${Math.floor(value / 60)} h ${Math.round(value % 60)} min`;
  }
}
