import { ChangeDetectionStrategy, Component, input, signal } from '@angular/core';

import { StatusBadgeComponent } from '../../../../../shared/ui/status-badge/status-badge';
import type { MonitoringServicesViewModel, ServiceStatusCard } from '../../../models/monitoring.model';

/**
 * Caja "Estado de servicios" del monitoreo GA03.
 *
 * Componente OnPush aislado: recibe el estado de servicios por input de señal
 * y su acordeón (abierto/cerrado) es estado local. Cuando el ETL corre y el
 * polling refresca la página cada segundo, solo las cajas cuyos datos cambian
 * re-evalúan su template — el resto de la página no.
 */
@Component({
  selector: 'app-mp-services-box',
  imports: [StatusBadgeComponent],
  templateUrl: './mp-services-box.html',
  styleUrl: './mp-services-box.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MpServicesBoxComponent {
  readonly services = input.required<MonitoringServicesViewModel>();

  readonly open = signal(false);

  toggleOpen() {
    this.open.update(v => !v);
  }

  serviceTone(tone: ServiceStatusCard['tone']): 'success' | 'warning' | 'danger' {
    return tone === 'muted' || tone === 'error' ? 'warning' : tone;
  }

  serviceLabel(tone: ServiceStatusCard['tone']): string {
    return tone === 'success' ? 'Disponible'
      : tone === 'warning' ? 'Atención'
      : tone === 'error' ? 'Error'
      : 'N/D';
  }
}
