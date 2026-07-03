import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-rd-history-panel',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (vm()?.cancellationPolicy; as policy) {
      <section class="surface-card panel policy-panel">
        <div class="panel-head">
          <div class="panel-head-left">
            <span class="material-symbols-outlined panel-icon">gavel</span>
            <h2>Política de cancelación</h2>
          </div>
        </div>
        <p class="policy-text">{{ policy }}</p>
      </section>
    }

    <section class="surface-card panel">
      <h2>Historial de estado</h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Status</th><th>Fecha</th><th>Motivo</th><th>Cambiado por</th></tr></thead>
          <tbody>
            @for (item of vm()?.history; track item.status + item.changedAt + item.reason) {
              <tr><td>{{ item.status }}</td><td>{{ item.changedAt }}</td><td>{{ item.reason }}</td><td>{{ item.changedBy }}</td></tr>
            }
          </tbody>
        </table>
      </div>
    </section>
  `
})
export class RdHistoryPanelComponent {
  readonly vm = input<any>(null);
}
