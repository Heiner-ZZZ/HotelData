import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import type { RoomFeatureItem, RoomTypeItem } from '../../models/rooms.model';

@Component({
  selector: 'app-room-type-table',
  templateUrl: './room-type-table.html',
  styleUrl: './room-type-table.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RoomTypeTableComponent {
  readonly items = input<RoomTypeItem[]>([]);
  readonly editRoom = output<RoomTypeItem>();
  readonly deleteRoom = output<{ id: string; name: string }>();

  onEdit(room: RoomTypeItem) {
    this.editRoom.emit(room);
  }

  onDelete(room: RoomTypeItem) {
    this.deleteRoom.emit({ id: room.id, name: room.name });
  }

  trackByFeature(_index: number, feature: RoomFeatureItem): string {
    return feature.label;
  }

  /** Map features to a simple color based on index for visual variety. */
  featureColor(feature: RoomFeatureItem): string {
    const colors = ['#3b82f6', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#6366f1'];
    const label = feature.label;
    let hash = 0;
    for (let i = 0; i < label.length; i++) {
      hash = ((hash << 5) - hash) + label.charCodeAt(i);
      hash |= 0;
    }
    return colors[Math.abs(hash) % colors.length];
  }
}