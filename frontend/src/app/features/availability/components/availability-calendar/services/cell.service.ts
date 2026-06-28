import { AvailabilityState } from '../../services/availability-state';
import { CalendarService } from './calendar.service';
import { InventoryService } from '../../data-tables/services/inventory.service';
import { BlackoutService } from '../../data-tables/services/blackout.service';
import { ToastService } from '../../../../../shared/services/toast.service';

export class CellService {
  constructor(
    private readonly state: AvailabilityState,
    private readonly calendar: CalendarService,
    private readonly inventory: InventoryService,
    private readonly blackout: BlackoutService,
    private readonly toast: ToastService,
  ) {}

  onClick(event: MouseEvent, date: string, roomTypeName: string) {
    if (this.state.multiSelectMode()) {
      // selection handled externally via ref to SelectionService
      return;
    }
    this.startEdit(date, roomTypeName);
  }

  startEdit(date: string, roomTypeName: string) {
    const current = this.state.editingCell();
    if (current?.date === date && current?.roomTypeName === roomTypeName) return;
    this.state.activeCell.set({ date, roomTypeName });
    this.state.editingCell.set({ date, roomTypeName });

    const vm = this.state.pageData();
    const rt = vm?.roomTypes.find((r) => r.name === roomTypeName);
    const inv = vm?.inventoryItems.find((i) => i.date === date && i.roomTypeName === roomTypeName);
    this.inventory.form.patchValue({
      roomTypeId: rt?.id ?? roomTypeName, date,
      totalRooms: inv?.totalRooms ?? 0,
      availableRooms: inv?.availableRooms ?? 0,
      blockedRooms: inv?.blockedRooms ?? 0,
    });
    this.inventory.onRoomTypeChange();
    setTimeout(() => {
      const el = document.querySelector<HTMLInputElement>('#cell-input-' + CSS.escape(date + roomTypeName));
      el?.focus();
      el?.select();
    }, 50);
  }

  commitEdit(date: string, roomTypeName: string, inputEl: HTMLInputElement | null) {
    const edit = this.state.editingCell();
    if (!edit || edit.date !== date || edit.roomTypeName !== roomTypeName) return;
    const raw = inputEl?.value ?? '';
    const val = parseInt(raw, 10);
    if (isNaN(val) || val < 0) { this.cancelEdit(); return; }

    const vm = this.state.pageData();
    const inv = vm?.inventoryItems.find((i) => i.date === date && i.roomTypeName === roomTypeName);
    const rt = vm?.roomTypes.find((r) => r.name === roomTypeName);
    const total = inv?.totalRooms ?? 0;
    const clamped = Math.min(val, total);

    this.inventory.form.patchValue({
      roomTypeId: rt?.id ?? roomTypeName, date,
      totalRooms: total, availableRooms: clamped, blockedRooms: total - clamped,
    });
    this.state.savingCell.set(`${date}|${roomTypeName}`);
    this.state.editingCell.set(null);
    this.inventory.save();
  }

  cancelEdit() { this.state.editingCell.set(null); this.state.savingCell.set(null); }

  isEditing(d: string, r: string) {
    return this.state.editingCell()?.date === d && this.state.editingCell()?.roomTypeName === r;
  }

  isSelected(d: string, r: string) {
    return this.state.activeCell()?.date === d && this.state.activeCell()?.roomTypeName === r;
  }

  quickBlock() {
    const cell = this.state.activeCell();
    if (!cell) return;
    const vm = this.state.pageData();
    const rt = vm?.roomTypes.find((rt) => rt.name === cell.roomTypeName);
    this.blackout.form.patchValue({
      roomTypeId: rt?.id ?? cell.roomTypeName,
      startDate: cell.date, endDate: cell.date,
      blockedRooms: 1, reason: 'Mantenimiento',
    });
    setTimeout(() => {
      document.querySelector('.form-card:has(#blk-start)')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      (document.getElementById('blk-start') as HTMLInputElement)?.focus();
    }, 150);
  }

  quickMarkUnavailable() {
    const cell = this.state.activeCell();
    if (!cell) return;
    const vm = this.state.pageData();
    const inv = vm?.inventoryItems.find((i) => i.date === cell.date && i.roomTypeName === cell.roomTypeName);
    this.state.confirmAction.set({
      title: 'Marcar como no disponible',
      message: `Se establecerán 0 habitaciones disponibles para ${cell.roomTypeName} el ${cell.date} (actualmente ${inv?.availableRooms ?? 0} de ${inv?.totalRooms ?? 0} disponibles). ¿Desea continuar?`,
      handler: () => this._executeQuickMarkUnavailable(),
    });
  }

  private _executeQuickMarkUnavailable() {
    const cell = this.state.activeCell();
    if (!cell) return;
    const vm = this.state.pageData();
    const inv = vm?.inventoryItems.find((i) => i.date === cell.date && i.roomTypeName === cell.roomTypeName);
    const rt = vm?.roomTypes.find((r) => r.name === cell.roomTypeName);
    const total = inv?.totalRooms ?? 1;
    this.state.undoState.set({
      date: cell.date, roomTypeName: cell.roomTypeName,
      roomTypeId: rt?.id ?? cell.roomTypeName,
      totalRooms: total, availableRooms: inv?.availableRooms ?? 0, blockedRooms: inv?.blockedRooms ?? 0,
    });
    this.inventory.form.patchValue({
      roomTypeId: rt?.id ?? cell.roomTypeName, date: cell.date,
      totalRooms: total, availableRooms: 0, blockedRooms: total,
    });
    this.state.savingCell.set(`${cell.date}|${cell.roomTypeName}`);
    this.inventory.save();
  }
}
