import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { RoomTypeTableComponent } from '../../../components/room-type-table/room-type-table';
import { EmptyStateComponent } from '../../../../../shared/ui/empty-state/empty-state';

@Component({
  selector: 'app-rp-tables',
  standalone: true,
  imports: [RoomTypeTableComponent, EmptyStateComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="surface-card data-panel" style="margin-bottom: 1.25rem">
      <div class="panel-head">
        <span class="material-symbols-outlined panel-head-icon">table</span>
        <div>
          <h2>Tipos de habitación</h2>
          <p>{{ vm()?.totalRoomTypes }} tipo(s) configurado(s).</p>
        </div>
      </div>
      @if (vm()?.roomTypes?.length) {
        <app-room-type-table [items]="vm()!.roomTypes" (editRoom)="editRoom.emit($event)" (deleteRoom)="deleteRoom.emit($event)" />
      } @else {
        <app-empty-state icon="meeting_room" title="Sin tipos de habitación" description="Comience creando el primero para poder cargar inventario." />
      }
    </section>

    <section class="surface-card data-panel">
      <div class="panel-head">
        <span class="material-symbols-outlined panel-head-icon icon-physical-amber">door_sliding</span>
        <div>
          <h2>Habitaciones físicas</h2>
          <p>{{ vm()?.totalHotelRooms }} registro(s) asociados.</p>
        </div>
      </div>
      @if (vm()?.hotelRooms?.length) {
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr><th>ID</th><th>N°</th><th>Piso</th><th>Tipo</th><th>Vista</th><th>Fumador</th><th>Accesible</th><th>Estado</th><th>Próxima ocupación</th></tr>
            </thead>
            <tbody>
              @for (room of vm()?.hotelRooms; track room.id) {
                <tr>
                  <td><code>{{ room.id }}</code></td>
                  <td><span class="material-symbols-outlined table-icon icon-data-blue">door_front</span> {{ room.roomNumber || '--' }}</td>
                  <td>{{ room.floor || '--' }}</td>
                  <td>{{ room.roomTypeName }}</td>
                  <td>{{ room.view || '--' }}</td>
                  <td>
                    <span class="badge-smoking" [class.yes]="room.smoking" [class.no]="!room.smoking">
                      <span class="material-symbols-outlined badge-icon">{{ room.smoking ? 'smoking_rooms' : 'smoke_free' }}</span>
                    </span>
                  </td>
                  <td>
                    <span class="badge-accessible" [class.yes]="room.accessible" [class.no]="!room.accessible">
                      <span class="material-symbols-outlined badge-icon">{{ room.accessible ? 'accessible' : 'accessible_forward' }}</span>
                    </span>
                  </td>
                  <td>
                    <span class="status-badge" [class.active]="room.activeLabel === 'Sí'" [class.inactive]="room.activeLabel !== 'Sí'">
                      <span class="material-symbols-outlined badge-icon">{{ room.activeLabel === 'Sí' ? 'check_circle' : 'cancel' }}</span>
                      {{ room.activeLabel === 'Sí' ? 'Activa' : 'Inactiva' }}
                    </span>
                  </td>
                  <td>
                    @if (room.isOccupiedSoon) {
                      <span class="occupancy-badge occupied" title="{{ room.occupancyLabel }}">
                        <span class="material-symbols-outlined badge-icon">event_busy</span> {{ room.occupancyLabel }}
                      </span>
                    } @else {
                      <span class="occupancy-badge free">
                        <span class="material-symbols-outlined badge-icon">check_circle</span> Disponible
                      </span>
                    }
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      } @else {
        <app-empty-state icon="door_sliding" title="Sin habitaciones físicas" description="Todavía no hay registros en hotel_rooms para esta propiedad." />
      }
    </section>
  `
})
export class RpTablesComponent {
  readonly vm = input<any>(null);
  readonly editRoom = output<any>();
  readonly deleteRoom = output<{ id: string; name: string }>();
}
