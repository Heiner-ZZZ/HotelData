import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-rd-assigned-rooms',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (vm()?.assignedRooms?.length > 0) {
      <section class="surface-card panel assigned-rooms-panel">
        <div class="panel-head">
          <div class="panel-head-left">
            <span class="material-symbols-outlined panel-icon">meeting_room</span>
            <h2>Habitaciones asignadas</h2>
          </div>
          <span class="panel-badge">{{ vm()?.assignedRooms?.length }} habitación(es)</span>
        </div>
        <div class="table-wrap">
          <table class="assigned-rooms-table">
            <thead>
              <tr><th>Habitación</th><th>Número</th><th>Piso</th><th>Estado</th></tr>
            </thead>
            <tbody>
              @for (r of vm()?.assignedRooms; track r.hotelRoomId) {
                <tr>
                  <td><strong>{{ r.roomLabel || r.hotelRoomId }}</strong></td>
                  <td>{{ r.roomNumber || '--' }}</td>
                  <td>{{ r.floor || '--' }}</td>
                  <td>
                    <span class="room-status-badge"
                      [class.rs-available]="r.roomStatus === 'available'"
                      [class.rs-occupied]="r.roomStatus === 'occupied'"
                      [class.rs-cleaning]="r.roomStatus === 'cleaning'"
                      [class.rs-clean]="r.roomStatus === 'clean'"
                      [class.rs-inspected]="r.roomStatus === 'inspected'"
                      [class.rs-dirty]="r.roomStatus === 'dirty'"
                      [class.rs-maintenance]="r.roomStatus === 'maintenance'"
                      [class.rs-out]="r.roomStatus === 'out_of_order' || r.roomStatus === 'out_of_service'"
                      [class.rs-unknown]="r.roomStatus === 'unknown'">
                      <span class="rs-dot"></span>
                      <span>
                        @switch (r.roomStatus) {
                          @case ('available') { Disponible }
                          @case ('occupied') { Ocupada }
                          @case ('cleaning') { Limpieza }
                          @case ('clean') { Limpia }
                          @case ('inspected') { Inspeccionada }
                          @case ('dirty') { Sucia }
                          @case ('maintenance') { Mantenimiento }
                          @case ('out_of_order') { Fuera de orden }
                          @case ('out_of_service') { Fuera de servicio }
                          @default { {{ r.roomStatus }} }
                        }
                      </span>
                    </span>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </section>
    }
  `
})
export class RdAssignedRoomsComponent {
  readonly vm = input<any>(null);
}
