import { DestroyRef } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';

import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import type { ApiError } from '../../../../../core/api/api-error.model';
import { AvailabilityState } from '../../../services/availability-state';
import { CalendarService } from '../../availability-calendar/services/calendar.service';
import { AvailabilityApiService } from '../../../services/availability-api.service';
import { ToastService } from '../../../../../shared/services/toast.service';

export class InventoryService {
  readonly form;

  constructor(
    private readonly state: AvailabilityState,
    private readonly calendar: CalendarService,
    private readonly api: AvailabilityApiService,
    private readonly destroyRef: DestroyRef,
    private readonly toast: ToastService,
    private readonly formBuilder: FormBuilder,
  ) {
    this.form = this.formBuilder.nonNullable.group({
      roomTypeId: ['', [Validators.required]],
      date: ['', [Validators.required]],
      totalRooms: [0, [Validators.required, Validators.min(0)]],
      availableRooms: [0, [Validators.required, Validators.min(0)]],
      blockedRooms: [0, [Validators.required, Validators.min(0)]],
    });
  }

  onEditFromTable(item: { date: string; roomTypeName: string; roomTypeId: string; totalRooms: number; availableRooms: number; blockedRooms: number }) {
    const vm = this.state.pageData();
    const rt = vm?.roomTypes.find((r) => r.name === item.roomTypeName);
    this.form.patchValue({
      roomTypeId: rt?.id ?? item.roomTypeId,
      date: item.date,
      totalRooms: item.totalRooms,
      availableRooms: item.availableRooms,
      blockedRooms: item.blockedRooms,
    });
    this.onRoomTypeChange();
    setTimeout(() => {
      document.getElementById('inventory-form-card')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);
  }

  onDeleteFromTable(item: { date: string; roomTypeName: string }) {
    this.state.inventoryDeleteConfirm.set({ date: item.date, roomTypeName: item.roomTypeName });
  }

  confirmDelete() {
    const payload = this.state.inventoryDeleteConfirm();
    if (!payload) return;
    this.state.inventoryDeleteConfirm.set(null);

    const propId = this.state.selectedPropId();
    if (!propId) return;
    const vm = this.state.pageData();
    const rt = vm?.roomTypes.find((r) => r.name === payload.roomTypeName);
    if (!rt) return;

    this.state.saving.set(true);
    this.api
      .deleteInventory(propId, rt.id, payload.date)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.state.reload();
          this.toast.success('Registro de inventario eliminado');
          this.state.saving.set(false);
        },
        error: (err: ApiError) => {
          this.toast.error(err.message || 'Error al eliminar registro de inventario.');
          this.state.saving.set(false);
        },
      });
  }

  save() {
    const propId = this.state.selectedPropId();
    if (!propId) { this.state.savingCell.set(null); return; }
    if (this.form.invalid) { this.form.markAllAsTouched(); this.state.savingCell.set(null); return; }

    this.state.saving.set(true);
    const f = this.form.controls;
    this.api
      .saveInventory({
        prop_id: propId,
        room_type_id: f.roomTypeId.value,
        date: f.date.value,
        total_rooms: f.totalRooms.value,
        available_rooms: f.availableRooms.value,
        blocked_rooms: f.blockedRooms.value,
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.state.reload();
          this.toast.success('Inventario actualizado');

          const savedKey = this.state.savingCell();
          this.state.savingCell.set(null);
          if (savedKey) {
            const f = this.form.controls;
            const label = `${f.availableRooms.value}/${f.totalRooms.value} disponibles`;
            this.state.highlightedCell.set({ key: savedKey, label });
            setTimeout(() => this.state.highlightedCell.set(null), 1200);
          }

          this.form.reset({ roomTypeId: '', date: '', totalRooms: 0, availableRooms: 0, blockedRooms: 0 });
          this.state.activeCell.set(null);
          this.state.editingCell.set(null);
          this.state.hotelRoomsForType.set([]);
          this.state.roomsForTypeId.set('');
          this.state.selectedAvailableRooms.set(new Set());
          this.state.selectedBlockedRooms.set(new Set());
          this.state.saving.set(false);

          if (this.state.undoState()) {
            if (this.state.undoTimer) clearTimeout(this.state.undoTimer);
            this.state.undoTimer = setTimeout(() => this.state.undoState.set(null), 10000);
          }
        },
        error: (err: ApiError) => {
          this.toast.error(err.message || 'Error al guardar inventario.');
          this.state.savingCell.set(null);
          this.state.saving.set(false);
          this.state.undoState.set(null);
          if (this.state.undoTimer) { clearTimeout(this.state.undoTimer); this.state.undoTimer = null; }
        },
      });
  }

  onRoomTypeChange() {
    const roomTypeId = this.form.controls.roomTypeId.value;
    const propId = this.state.selectedPropId();
    if (!roomTypeId || !propId) {
      this.state.hotelRoomsForType.set([]);
      this.state.roomsForTypeId.set('');
      this.state.selectedAvailableRooms.set(new Set());
      this.state.selectedBlockedRooms.set(new Set());
      return;
    }
    this.api.getHotelRooms(propId, roomTypeId).subscribe({
      next: (res) => {
        this.state.hotelRoomsForType.set(res.items);
        this.state.roomsForTypeId.set(roomTypeId);
        this.state.selectedAvailableRooms.set(new Set(res.items.map((r) => r.room_number)));
        this.state.selectedBlockedRooms.set(new Set());
        this._syncFormFromCheckboxes();
      },
      error: () => {
        this.state.hotelRoomsForType.set([]);
        this.state.roomsForTypeId.set('');
      },
    });
  }

  toggleRoom(roomNumber: string) {
    const available = new Set(this.state.selectedAvailableRooms());
    const blocked = new Set(this.state.selectedBlockedRooms());
    if (available.has(roomNumber)) {
      available.delete(roomNumber);
      blocked.add(roomNumber);
    } else if (blocked.has(roomNumber)) {
      blocked.delete(roomNumber);
      available.add(roomNumber);
    } else {
      available.add(roomNumber);
    }
    this.state.selectedAvailableRooms.set(available);
    this.state.selectedBlockedRooms.set(blocked);
    this._syncFormFromCheckboxes();
  }

  private _syncFormFromCheckboxes() {
    const totals = this.state.computedInventoryTotals();
    this.form.patchValue({
      totalRooms: totals.total,
      availableRooms: totals.available,
      blockedRooms: totals.blocked,
    });
  }
}
