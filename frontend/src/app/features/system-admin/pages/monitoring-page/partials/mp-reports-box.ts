import { ChangeDetectionStrategy, Component, input, signal } from '@angular/core';

import { StatusBadgeComponent } from '../../../../../shared/ui/status-badge/status-badge';
import type { ReportItem } from '../../../models/monitoring.model';

/**
 * Caja "Reportes" del monitoreo GA03 (evidencia local del ETL).
 *
 * Componente OnPush aislado: recibe los reportes por input de señal y su
 * acordeón (abierto/cerrado) es estado local. Con el polling del ETL, solo
 * las cajas cuyos datos cambian re-evalúan su template.
 */
@Component({
  selector: 'app-mp-reports-box',
  imports: [StatusBadgeComponent],
  templateUrl: './mp-reports-box.html',
  styleUrl: './mp-reports-box.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MpReportsBoxComponent {
  readonly reports = input.required<ReportItem[]>();

  readonly open = signal(false);

  toggleOpen() {
    this.open.update(v => !v);
  }
}
