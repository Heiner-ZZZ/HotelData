import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({
  selector: 'app-rd-room-modal',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (show()) {
      <div class="modal-overlay" (click)="close.emit()">
        <div class="modal-panel room-modal" (click)="$event.stopPropagation()">
          <div class="modal-head">
            <span class="material-symbols-outlined modal-head-icon">meeting_room</span>
            <div>
              <h2>Asignar habitaciones</h2>
              <p>{{ bookingId() }} — {{ hotelLabel() }}</p>
            </div>
            <button type="button" class="modal-close" (click)="close.emit()" aria-label="Cerrar">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
          <div class="modal-body">
            @if (assignmentState() === 'loading') {
              <div class="loading-shade-sm">
                <span class="material-symbols-outlined loading-spin">sync</span>
                <span>Cargando habitaciones disponibles...</span>
              </div>
            } @else if (assignmentState() === 'error') {
              <div class="error-msg">
                <span class="material-symbols-outlined">error</span>
                <span>No se pudieron cargar las habitaciones disponibles.</span>
              </div>
            } @else {
              @if (message()) {
                <div class="toast toast-error" style="margin-bottom: 12px;">{{ message() }}</div>
              }
              <div class="room-assignment-info">
                <span class="badge-required">Requiere {{ roomsRequired() }} habitación(es)</span>
                <span class="badge-selected">{{ selectedRoomIds().size }} seleccionada(s)</span>
              </div>
              @if (availableRooms().length === 0) {
                <div class="empty-rooms">
                  <span class="material-symbols-outlined">meeting_room</span>
                  <p>No hay habitaciones físicas disponibles para esta reserva.</p>
                  <p class="hint">Configura las habitaciones en Gestión &gt; Habitaciones primero.</p>
                </div>
              } @else {
                <div class="rooms-checklist">
                  @for (room of availableRooms(); track room.hotel_room_id) {
                    <label class="room-check-item"
                      [class.is-selected]="selectedRoomIds().has(room.hotel_room_id)"
                      [class.is-assigned]="assignedRoomIds().includes(room.hotel_room_id)">
                      <input type="checkbox"
                        [checked]="selectedRoomIds().has(room.hotel_room_id)"
                        (change)="toggleRoom.emit(room.hotel_room_id)"
                        [disabled]="assignedRoomIds().includes(room.hotel_room_id) && !selectedRoomIds().has(room.hotel_room_id)" />
                      <span class="material-symbols-outlined room-icon">door_front</span>
                      <div class="room-info">
                        <strong>{{ room.room_label || room.room_number || room.hotel_room_id }}</strong>
                        <div class="room-meta">
                          @if (room.room_number) { <span class="room-number">N° {{ room.room_number }}</span> }
                          @if (room.floor) { <span class="room-floor">Piso {{ room.floor }}</span> }
                        </div>
                        <span class="room-status-badge room-status-badge--sm"
                          [class.rs-available]="room.room_status === 'available'"
                          [class.rs-occupied]="room.room_status === 'occupied'"
                          [class.rs-cleaning]="room.room_status === 'cleaning'"
                          [class.rs-clean]="room.room_status === 'clean'"
                          [class.rs-inspected]="room.room_status === 'inspected'"
                          [class.rs-dirty]="room.room_status === 'dirty'"
                          [class.rs-maintenance]="room.room_status === 'maintenance'"
                          [class.rs-out]="room.room_status === 'out_of_order' || room.room_status === 'out_of_service'"
                          [class.rs-unknown]="!room.room_status || room.room_status === 'unknown'">
                          <span class="rs-dot"></span>
                          <span>
                            @switch (room.room_status) {
                              @case ('available') { Disponible }
                              @case ('occupied') { Ocupada }
                              @case ('cleaning') { Limpieza }
                              @case ('clean') { Limpia }
                              @case ('inspected') { Inspeccionada }
                              @case ('dirty') { Sucia }
                              @case ('maintenance') { Mantenimiento }
                              @case ('out_of_order') { Fuera de orden }
                              @case ('out_of_service') { Fuera de servicio }
                              @default { {{ room.room_status || 'Desconocido' }} }
                            }
                          </span>
                        </span>
                      </div>
                      @if (assignedRoomIds().includes(room.hotel_room_id)) {
                        <span class="assigned-badge">Asignada</span>
                      }
                    </label>
                  }
                </div>
              }
            }
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" (click)="close.emit()">Cancelar</button>
            <button type="button" class="btn-primary"
              (click)="save.emit()"
              [disabled]="saving() || selectedRoomIds().size === 0">
              @if (saving()) {
                <span class="material-symbols-outlined loading-spin">sync</span>
                Asignando...
              } @else {
                <span class="material-symbols-outlined">check</span>
                Asignar {{ selectedRoomIds().size }} habitación(es)
              }
            </button>
          </div>
        </div>
      </div>
    }
  `
})
export class RdRoomModalComponent {
  readonly show = input(false);
  readonly bookingId = input<string>('');
  readonly hotelLabel = input<string>('');
  readonly assignmentState = input<string>('idle');
  readonly availableRooms = input<any[]>([]);
  readonly assignedRoomIds = input<string[]>([]);
  readonly selectedRoomIds = input<Set<string>>(new Set());
  readonly roomsRequired = input(0);
  readonly saving = input(false);
  readonly message = input<string>('');

  readonly close = output<void>();
  readonly toggleRoom = output<string>();
  readonly save = output<void>();
}
