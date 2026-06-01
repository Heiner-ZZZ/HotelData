import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import type { RoomTypeItem } from '../../models/rooms.model';

@Component({
  selector: 'app-room-type-table',
  standalone: true,
  imports: [StatusBadgeComponent],
  templateUrl: './room-type-table.html',
  styleUrl: './room-type-table.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RoomTypeTableComponent {
  readonly items = input.required<RoomTypeItem[]>();
}
