import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';

import { StatusBadgeComponent } from '../../../../../shared/ui/status-badge/status-badge';
import { InfoTooltipComponent } from '../../../../../shared/ui/info-tooltip/info-tooltip.component';
import type { Ga03ProgressInfo } from '../../../models/monitoring.model';

/**
 * Caja "Progreso ETL" del monitoreo GA03 (PocketBase → MongoDB).
 *
 * Componente OnPush aislado: recibe el progreso del ETL por inputs de señal y
 * solo su vista se re-renderiza cuando cambia el progreso real que llega por
 * polling. El resto de la página no se re-renderiza con cada tick.
 */
@Component({
  selector: 'app-mp-etl-progress-box',
  imports: [StatusBadgeComponent, InfoTooltipComponent],
  templateUrl: './mp-etl-progress-box.html',
  styleUrl: './mp-etl-progress-box.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MpEtlProgressBoxComponent {
  /** Progreso del ETL GA03 — cambia en tiempo real con el polling. */
  readonly progress = input.required<Ga03ProgressInfo>();
  readonly targetPocketbase = input.required<number>();
  readonly targetMongodb = input.required<number>();
  readonly incrementalMode = input(false);
  readonly actionBusy = input(false);

  readonly stopSeed = output<void>();
  readonly stopPipeline = output<void>();
  readonly seed = output<void>();
  readonly validate = output<void>();
  readonly pipeline = output<void>();
  readonly clearEvidence = output<void>();
  readonly targetPocketbaseChange = output<number>();
  readonly targetMongodbChange = output<number>();
  readonly incrementalModeChange = output<void>();

  readonly open = signal(false);

  readonly isRunning = computed(() => this.progress().isRunning);
  readonly etlModeLabel = computed(() => this.incrementalMode() ? 'Incremental' : 'Completo');

  readonly targetOptions = Array.from({ length: 16 }, (_, i) => {
    const val = (i + 1) * 100000;
    return { value: val, label: val.toLocaleString('es') };
  });

  toggleOpen() {
    this.open.update(v => !v);
  }

  statusTone(status: string): 'success' | 'warning' | 'danger' {
    if (status === 'completed') return 'success';
    if (status === 'failed') return 'danger';
    return 'warning';
  }
}