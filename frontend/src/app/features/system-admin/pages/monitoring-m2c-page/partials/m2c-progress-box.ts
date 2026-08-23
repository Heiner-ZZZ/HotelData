import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';

import { StatusBadgeComponent } from '../../../../../shared/ui/status-badge/status-badge';
import type { M2cProgressDto } from '../../../models/monitoring-m2c.dto';

/** Orden canónico de los pasos del pipeline M2C (mismo del backend). */
export const M2C_STEP_ORDER = [
  'validate_config',
  'extract_mongo',
  'transform',
  'create_tables',
  'load_clickhouse',
  'quality_report',
  'execution_report',
] as const;

/**
 * Caja "ETL pipeline progress" del monitoreo M2C (MongoDB → ClickHouse).
 *
 * Componente OnPush aislado: recibe el progreso del pipeline por input de
 * señal y solo su vista se re-renderiza cuando cambia el progreso real que
 * llega por polling (KPIs: percent/elapsed/status + pasos del pipeline).
 * El resto de la página no re-evalúa esta sección con cada tick.
 */
@Component({
  selector: 'app-m2c-progress-box',
  imports: [StatusBadgeComponent],
  templateUrl: './m2c-progress-box.html',
  styleUrl: './m2c-progress-box.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class M2cProgressBoxComponent {
  /** Progreso del pipeline M2C — cambia en tiempo real con el polling. */
  readonly progress = input.required<M2cProgressDto>();
  readonly actionBusy = input(false);

  readonly run = output<void>();
  readonly stop = output<void>();

  readonly open = signal(false);

  readonly stepOrder = M2C_STEP_ORDER;

  readonly isRunning = computed(() => this.progress().is_running);

  toggleOpen() {
    this.open.update(v => !v);
  }

  statusTone(status: string): 'success' | 'warning' | 'danger' {
    if (status === 'completed' || status === 'success') return 'success';
    if (status === 'failed') return 'danger';
    return 'warning';
  }
}
