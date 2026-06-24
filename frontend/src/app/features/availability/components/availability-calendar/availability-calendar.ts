import { ChangeDetectionStrategy, Component, computed, input, output, ViewEncapsulation } from '@angular/core';

import type { AvailabilityRoomType, CalendarMonth, CalendarRoomTypeCell } from '../../models/availability.model';

@Component({
  selector: 'app-availability-calendar',
  imports: [],
  templateUrl: './availability-calendar.html',
  styleUrl: '../../pages/availability-page/availability-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
})
export class AvailabilityCalendarComponent {
  readonly calendar = input<CalendarMonth | null>(null);
  readonly roomTypes = input<AvailabilityRoomType[]>([]);
  readonly viewMode = input<'month' | 'week'>('month');
  readonly multiSelectMode = input(false);
  readonly saving = input(false);
  readonly savingCell = input<string | null>(null);
  readonly highlightedCell = input<{ key: string; label: string } | null>(null);
  readonly skeletonCols = input<number[]>([]);
  readonly editingCell = input<{ date: string; roomTypeName: string } | null>(null);
  readonly activeCell = input<{ date: string; roomTypeName: string } | null>(null);
  readonly selectedCells = input<Set<string>>(new Set());
  readonly refreshing = input(false);
  readonly skeletonExiting = input(false);
  readonly selectionCount = input(0);
  readonly layoutMode = input<'scroll' | 'wrap'>('scroll');

  readonly prevPeriod = output<void>();
  readonly nextPeriod = output<void>();
  readonly goToday = output<void>();
  readonly setView = output<'month' | 'week'>();
  readonly toggleMultiSelect = output<boolean>();
  readonly cellClick = output<{ event: MouseEvent; date: string; roomTypeName: string }>();
  readonly commitEdit = output<{ date: string; roomTypeName: string; input: HTMLInputElement | null }>();
  readonly cancelEditOutput = output<void>();
  readonly toggleLayout = output<'scroll' | 'wrap'>();

  onPrev() { this.prevPeriod.emit(); }
  onNext() { this.nextPeriod.emit(); }
  onGoToday() { this.goToday.emit(); }
  onSetView(mode: 'month' | 'week') { this.setView.emit(mode); }
  onToggleMultiSelect(enabled: boolean) { this.toggleMultiSelect.emit(enabled); }
  onCellClick(event: MouseEvent, date: string, roomTypeName: string) { this.cellClick.emit({ event, date, roomTypeName }); }
  onCommitEdit(date: string, roomTypeName: string, input: HTMLInputElement | null) { this.commitEdit.emit({ date, roomTypeName, input }); }
  onCancelEdit() { this.cancelEditOutput.emit(); }
  onToggleLayout(mode: 'scroll' | 'wrap') { this.toggleLayout.emit(mode); }

  // ── Pure computation methods (moved from parent) ──

  cellClass(roomType: CalendarRoomTypeCell): string {
    if (roomType.totalRooms === 0) return 'cell-na';
    const pct = roomType.occupancyPct;
    if (pct >= 90) return 'cell-danger';
    if (pct >= 60) return 'cell-warning';
    if (pct >= 30) return 'cell-caution';
    return 'cell-good';
  }

  cellLabel(roomType: CalendarRoomTypeCell): string {
    if (roomType.totalRooms === 0) return '—';
    return `${roomType.availableRooms}/${roomType.totalRooms}`;
  }

  cellTooltip(roomType: CalendarRoomTypeCell, date: string): string {
    return `${date} · ${roomType.roomTypeName}: ${roomType.availableRooms}/${roomType.totalRooms} disponibles (${roomType.occupancyPct}% ocupado)`;
  }

  isEditing(date: string, roomTypeName: string): boolean {
    const cell = this.editingCell();
    return cell?.date === date && cell?.roomTypeName === roomTypeName;
  }

  isSelected(date: string, roomTypeName: string): boolean {
    const cell = this.activeCell();
    return cell?.date === date && cell?.roomTypeName === roomTypeName;
  }

  isMultiSelected(date: string, roomTypeName: string): boolean {
    return this.selectedCells().has(`${date}|${roomTypeName}`);
  }

  /** Group days into weeks (chunks of 7) for the wrap layout. */
  readonly weekChunks = computed(() => {
    const cal = this.calendar();
    if (!cal) return [];
    const chunks: typeof cal.days[] = [];
    for (let i = 0; i < cal.days.length; i += 7) {
      chunks.push(cal.days.slice(i, i + 7));
    }
    return chunks;
  });

  readonly avgOccupancy = computed(() => {
    const cal = this.calendar();
    if (!cal) return 0;
    const daysWithData = cal.days.filter(d => d.roomTypes.length > 0).length;
    if (daysWithData === 0) return 0;
    return cal.days.reduce((sum, d) => {
      const pcts = d.roomTypes.map(r => r.occupancyPct);
      return sum + (pcts.length > 0 ? pcts.reduce((a, b) => a + b, 0) / pcts.length : 0);
    }, 0) / daysWithData;
  });
}
