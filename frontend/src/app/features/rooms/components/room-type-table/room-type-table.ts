import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import type { RoomTypeItem } from '../../models/rooms.model';

@Component({
  selector: 'app-room-type-table',
  templateUrl: './room-type-table.html',
  styleUrl: './room-type-table.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RoomTypeTableComponent {
  readonly items = input<RoomTypeItem[]>([]);
  readonly editRoom = output<RoomTypeItem>();

  onEdit(room: RoomTypeItem) {
    this.editRoom.emit(room);
  }
}