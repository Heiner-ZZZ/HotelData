import { ChangeDetectionStrategy, Component, computed, input, output, ViewEncapsulation } from '@angular/core';

import type { AvailabilityRoomType, CalendarMonth } from '../../models/availability.model';
import { cellClass, cellLabel, cellTooltip } from '../../availability.helpers';

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
  /** Map room type ID → sorted room numbers for display in row headers. */
  readonly roomNumbersByType = input<Map<string, string[]>>(new Map());
  readonly avgOccupancy = input(0);

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

  // ── Pure computation methods ──

  cellClass = cellClass;
  cellLabel = cellLabel;
  cellTooltip = cellTooltip;

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

  /**
   * Noches ÚNICAS del rango con disponibilidad pero sin tarifa abierta
   * (no vendibles en el search público) — contador resumen del pie.
   */
  readonly noRateNights = computed(() => {
    const cal = this.calendar();
    if (!cal) return 0;
    const dates = new Set<string>();
    for (const day of cal.days) {
      const hasNoRate = day.roomTypes.some(
        (cell) => cell.availableRooms > 0 && cell.hasRate === false,
      );
      if (hasNoRate) dates.add(day.date);
    }
    return dates.size;
  });

}
