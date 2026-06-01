import { Component, input } from '@angular/core';

import type { RoomTypeItem } from '../../models/rooms.model';

@Component({
  selector: 'app-room-type-table',
  templateUrl: './room-type-table.html',
  styleUrl: './room-type-table.scss'
})
export class RoomTypeTableComponent {
  readonly items = input<RoomTypeItem[]>([]);
}
