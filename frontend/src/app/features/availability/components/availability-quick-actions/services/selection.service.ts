import { computed, DestroyRef } from '@angular/core';
import { switchMap } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import type { ApiError } from '../../../../../core/api/api-error.model';
import { AvailabilityState } from '../../../services/availability-state';
import { CalendarService } from '../../availability-calendar/services/calendar.service';
import { AvailabilityApiService } from '../../../services/availability-api.service';
import { ToastService } from '../../../../../shared/services/toast.service';

export class SelectionService {
  constructor(
    private readonly state: AvailabilityState,
    private readonly calendar: CalendarService,
    private readonly api: AvailabilityApiService,
    private readonly destroyRef: DestroyRef,
    private readonly toast: ToastService,
  ) {}

  readonly selectionCount = computed(() => this.state.selectedCells().size);

  readonly selectionGroups = computed(() => {
    const groups = new Map<string, { roomTypeName: string; dates: string[] }>();
    for (const key of this.state.selectedCells()) {
      const [date, roomTypeName] = key.split('|');
      if (!groups.has(roomTypeName)) {
        groups.set(roomTypeName, { roomTypeName, dates: [] });
      }
      groups.get(roomTypeName)!.dates.push(date);
    }
    return [...groups.values()];
  });

  readonly selectionSummary = computed(() => {
    const count = this.state.selectedCells().size;
    if (count === 0) return '';
    const groups = this.selectionGroups();
    if (groups.length === 1) {
      const g = groups[0];
      const sorted = [...g.dates].sort();
      return `${count} celdas · ${g.roomTypeName} · ${sorted.length > 1 ? `${sorted[0]} → ${sorted[sorted.length - 1]}` : sorted[0]}`;
    }
    return `${count} celdas · ${groups.length} tipo(s) de habitación`;
  });

  toggleMultiSelect(enabled: boolean) {
    this.state.multiSelectMode.set(enabled);
    if (enabled) {
      this.state.activeCell.set(null);
      this.state.editingCell.set(null);
    } else {
      this.state.selectedCells.set(new Set());
      this.state.clearLastCellKey();
    }
  }

  clearSelection() {
    this.state.selectedCells.set(new Set());
    this.state.clearLastCellKey();
  }

  selectAllCells() {
    const cal = this.calendar.displayCalendar();
    const vm = this.state.pageData();
    if (!cal || !vm) return;

    const all = new Set<string>();
    for (const day of cal.days) {
      for (const rt of vm.roomTypes) {
        all.add(`${day.date}|${rt.name}`);
      }
    }
    this.state.selectedCells.set(all);
    if (all.size > 0) {
      const lastDay = cal.days[cal.days.length - 1];
      const lastRt = vm.roomTypes[vm.roomTypes.length - 1];
      this.state.lastCellKey = `${lastDay.date}|${lastRt.name}`;
    }
  }

  toggleCell(date: string, roomTypeName: string) {
    const key = `${date}|${roomTypeName}`;
    const current = this.state.selectedCells();
    const next = new Set(current);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    this.state.selectedCells.set(next);
  }

  rangeSelect(date: string, roomTypeName: string) {
    if (!this.state.hasLastCellKey()) {
      this.toggleCell(date, roomTypeName);
      return;
    }
    const [lastDate, lastName] = this.state.lastCellKey.split('|');
    if (lastName !== roomTypeName) {
      this.toggleCell(date, roomTypeName);
      return;
    }
    const cal = this.calendar.displayCalendar();
    if (!cal) return;

    const idxA = cal.days.findIndex((d) => d.date === lastDate);
    const idxB = cal.days.findIndex((d) => d.date === date);
    if (idxA === -1 || idxB === -1) return;

    const [start, end] = idxA < idxB ? [idxA, idxB] : [idxB, idxA];
    const current = this.state.selectedCells();
    const next = new Set(current);
    for (let i = start; i <= end; i++) {
      next.add(`${cal.days[i].date}|${roomTypeName}`);
    }
    this.state.selectedCells.set(next);
  }

  batchMarkUnavailable() {
    const propId = this.state.selectedPropId();
    const vm = this.state.pageData();
    if (!propId || !vm) return;

    const cells: Array<{ date: string; roomTypeName: string; roomTypeId: string; totalRooms: number }> = [];
    for (const key of this.state.selectedCells()) {
      const [date, roomTypeName] = key.split('|');
      const invItem = vm.inventoryItems.find((i) => i.date === date && i.roomTypeName === roomTypeName);
      const rt = vm.roomTypes.find((r) => r.name === roomTypeName);
      cells.push({ date, roomTypeName, roomTypeId: rt?.id ?? roomTypeName, totalRooms: invItem?.totalRooms ?? 0 });
    }
    if (cells.length === 0) return;

    const targetAvail = Math.max(0, this.state.batchAvailableValue());
    this.state.saving.set(true);

    let completed = 0;
    const total = cells.length;

    for (const cell of cells) {
      const avail = Math.min(targetAvail, cell.totalRooms);
      const blocked = cell.totalRooms - avail;

      this.api
        .saveInventory({ prop_id: propId, room_type_id: cell.roomTypeId, date: cell.date, total_rooms: cell.totalRooms, available_rooms: avail, blocked_rooms: blocked })
        .pipe(switchMap(() => this.api.getAvailability(propId, 92)), takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (data) => {
            completed++;
            this.state.pageData.set(data);
            this.toast.success(`${avail === 0 ? 'no disponible' : `${avail} disponibles`} (${completed}/${total})`);
            this.calendar.rebuildCalendar();
            if (completed >= total) {
              this.state.selectedCells.set(new Set());
              this.state.clearLastCellKey();
              this.state.saving.set(false);
              const label = avail === 0 ? 'no disponible' : `${avail} disponibles`;
              this.state.highlightedCell.set({ key: `${cell.date}|${cell.roomTypeName}`, label });
              setTimeout(() => this.state.highlightedCell.set(null), 1200);
            }
          },
          error: (err: ApiError) => {
            this.toast.error(err.message || 'Error al actualizar disponibilidad.');
            this.state.saving.set(false);
          },
        });
    }
  }

  blockSelectedRange() {
    const propId = this.state.selectedPropId();
    const groups = this.selectionGroups();
    const vm = this.state.pageData();
    if (!propId || groups.length === 0 || !vm) return;

    let completed = 0;
    const total = groups.length;
    this.state.saving.set(true);

    for (const group of groups) {
      const sorted = [...group.dates].sort();
      const rt = vm.roomTypes.find((r) => r.name === group.roomTypeName);

      this.api
        .createBlackout({
          prop_id: propId,
          room_type_id: rt?.id ?? group.roomTypeName,
          start_date: sorted[0],
          end_date: sorted[sorted.length - 1],
          blocked_rooms: 1,
          reason: 'Mantenimiento',
        })
        .pipe(switchMap(() => this.api.getAvailability(propId, 92)), takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (data) => {
            completed++;
            this.state.pageData.set(data);
            this.toast.success(`Bloqueo registrado (${completed}/${total})`);
            this.calendar.rebuildCalendar();
            if (completed >= total) {
              this.state.selectedCells.set(new Set());
              this.state.clearLastCellKey();
              this.state.saving.set(false);
            }
          },
          error: (err: ApiError) => {
            this.toast.error(err.message || 'Error al registrar bloqueo.');
            this.state.saving.set(false);
          },
        });
    }
  }

  undoQuickAction() {
    const state = this.state.undoState();
    if (!state) return;
    this.state.undoState.set(null);
    this._clearUndoTimer();
    // The store will handle patching the form and saving
    return state;
  }

  dismissUndo() {
    this.state.undoState.set(null);
    this._clearUndoTimer();
  }

  private _clearUndoTimer() {
    if (this.state.undoTimer) {
      clearTimeout(this.state.undoTimer);
      this.state.undoTimer = null;
    }
  }
}
