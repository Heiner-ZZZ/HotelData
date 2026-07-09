import { ChangeDetectionStrategy, Component, input } from '@angular/core';

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pendiente',
  confirmed: 'Confirmada',
  checked_in: 'Check-in',
  checked_out: 'Check-out',
  cancelled: 'Cancelada',
  rejected: 'Rechazada',
  no_show: 'No show',
  completed: 'Completada',
  in_house: 'En casa',
  active: 'Activa',
  lost: 'Perdida',
};

@Component({
  selector: 'app-rd-history-panel',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="surface-card panel">
      <h2>Historial de estado</h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Estado</th><th>Fecha</th><th>Motivo</th><th>Cambiado por</th></tr></thead>
          <tbody>
            @for (item of vm()?.history; track item.status + item.changedAt + item.reason) {
              <tr>
                <td>
                  <span class="status-badge" [class]="'status--' + item.status">
                    {{ STATUS_LABELS[item.status] || item.status }}
                  </span>
                </td>
                <td>{{ item.changedAt }}</td>
                <td>{{ item.reason }}</td>
                <td>{{ item.changedBy }}</td>
              </tr>
            }
          </tbody>
        </table>
      </div>
    </section>
  `
})
export class RdHistoryPanelComponent {
  readonly vm = input<any>(null);

  readonly STATUS_LABELS = STATUS_LABELS;
}

