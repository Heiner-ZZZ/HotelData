import { ChangeDetectionStrategy, Component, input, signal } from '@angular/core';

import { StatusBadgeComponent } from '../../../../../shared/ui/status-badge/status-badge';
import type { MonitoringViewModel } from '../../../models/monitoring.model';

/** Resumen de la corrida ETL más reciente del monitoreo GA03. */
export type MpExecution = NonNullable<MonitoringViewModel['execution']>;

/**
 * Caja "Última ejecución" del monitoreo GA03.
 *
 * Componente OnPush aislado: recibe la ejecución por input de señal y su
 * acordeón (abierto/cerrado) es estado local. Con `execution === null` no
 * renderiza nada (el padre siempre pasa vm.execution). Con el polling del
 * ETL, solo esta caja re-evalúa su template cuando la corrida cambia.
 */
@Component({
  selector: 'app-mp-execution-box',
  imports: [StatusBadgeComponent],
  templateUrl: './mp-execution-box.html',
  styleUrl: './mp-execution-box.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MpExecutionBoxComponent {
  readonly execution = input<MpExecution | null>(null);

  readonly open = signal(false);

  toggleOpen() {
    this.open.update(v => !v);
  }

  statusTone(status: string): 'success' | 'warning' | 'danger' {
    if (status === 'success') return 'success';
    if (status === 'failed') return 'danger';
    return 'warning';
  }
}
