import { DestroyRef } from '@angular/core';
import { FormBuilder, Validators } from '@angular/forms';

import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import type { ApiError } from '../../../../../core/api/api-error.model';
import { AvailabilityState } from '../../../services/availability-state';
import { CalendarService } from '../../availability-calendar/services/calendar.service';
import { AvailabilityApiService } from '../../../services/availability-api.service';
import { ToastService } from '../../../../../shared/services/toast.service';

export class BlackoutService {
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
      startDate: ['', [Validators.required]],
      endDate: ['', [Validators.required]],
      blockedRooms: [0, [Validators.required, Validators.min(0)]],
      reason: [''],
    });
  }

  onEdit(blackoutId: string) {
    const vm = this.state.pageData();
    if (!vm) return;
    const item = vm.blackoutItems.find((b) => b.blackoutId === blackoutId);
    if (!item) return;
    const [startDate, endDate] = item.rangeLabel.split(' -> ');

    this.form.patchValue({
      roomTypeId: item.roomTypeId,
      startDate,
      endDate,
      blockedRooms: item.blockedRooms,
      reason: item.reason,
    });
    this.state.editingBlackout.set({
      blackoutId,
      roomTypeId: item.roomTypeId,
      startDate,
      endDate,
      reason: item.reason,
      roomNumbers: item.roomNumbers || [],
    });

    const propId = this.state.selectedPropId();
    if (propId && item.roomTypeId) {
      this.api.getHotelRooms(propId, item.roomTypeId).subscribe({
        next: (res) => {
          this.state.hotelRoomsForType.set(res.items);
          this.state.roomsForTypeId.set(item.roomTypeId);
          this.state.blackoutSelectedRooms.set(new Set(item.roomNumbers || []));
        },
        error: () => this.state.roomsForTypeId.set(''),
      });
    }
    setTimeout(() => {
      document.querySelector('.form-card:has(#blk-start)')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);
  }

  onDelete(blackoutId: string) {
    this.state.deleteConfirm.set({ blackoutId });
  }

  confirmDelete() {
    const payload = this.state.deleteConfirm();
    if (!payload) return;
    this.state.deleteConfirm.set(null);
    this.state.saving.set(true);

    this.api
      .deleteBlackout(payload.blackoutId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.state.reload();
          this.toast.success('Bloqueo eliminado correctamente');
          this.state.saving.set(false);
        },
        error: (err: ApiError) => {
          this.toast.error(err.message || 'Error al eliminar bloqueo.');
          this.state.saving.set(false);
        },
      });
  }

  cancelEdit() {
    this.state.editingBlackout.set(null);
    this.form.reset({ roomTypeId: '', startDate: '', endDate: '', blockedRooms: 0, reason: '' });
    this.state.blackoutSelectedRooms.set(new Set());
  }

  save() {
    const propId = this.state.selectedPropId();
    if (!propId || this.form.invalid) { this.form.markAllAsTouched(); return; }

    const roomNumbers = [...this.state.blackoutSelectedRooms()];
    if (roomNumbers.length > 0) {
      this.form.patchValue({ blockedRooms: roomNumbers.length });
    }

    this.state.saving.set(true);
    const editing = this.state.editingBlackout();
    const payload: Record<string, unknown> = {
      prop_id: propId,
      room_type_id: this.form.controls.roomTypeId.value,
      start_date: this.form.controls.startDate.value,
      end_date: this.form.controls.endDate.value,
      reason: this.form.controls.reason.value,
    };
    if (roomNumbers.length > 0) payload['room_numbers'] = roomNumbers;
    else payload['blocked_rooms'] = Math.max(1, Number(this.form.controls.blockedRooms.value) || 1);

    const request$ = editing ? this.api.updateBlackout(editing.blackoutId, payload) : this.api.createBlackout(payload as any);

    request$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.state.reload();
          this.toast.success('Bloqueo registrado');
          this.form.reset({ roomTypeId: '', startDate: '', endDate: '', blockedRooms: 0, reason: '' });
          this.state.editingBlackout.set(null);
          this.state.blackoutSelectedRooms.set(new Set());
          this.state.hotelRoomsForType.set([]);
          this.state.roomsForTypeId.set('');
          this.state.saving.set(false);
        },
        error: (err: ApiError) => {
          this.toast.error(err.message || 'Error al registrar bloqueo.');
          this.state.saving.set(false);
        },
      });
  }

  onRoomTypeChange() {
    const roomTypeId = this.form.controls.roomTypeId.value;
    const propId = this.state.selectedPropId();
    if (!roomTypeId || !propId) {
      this.state.blackoutSelectedRooms.set(new Set());
      return;
    }
    this.api.getHotelRooms(propId, roomTypeId).subscribe({
      next: (res) => {
        this.state.hotelRoomsForType.set(res.items);
        this.state.roomsForTypeId.set(roomTypeId);
        this.state.blackoutSelectedRooms.set(new Set());
      },
      error: () => this.state.roomsForTypeId.set(''),
    });
  }

  toggleRoom(roomNumber: string) {
    const selected = new Set(this.state.blackoutSelectedRooms());
    if (selected.has(roomNumber)) selected.delete(roomNumber);
    else selected.add(roomNumber);
    this.state.blackoutSelectedRooms.set(selected);
  }
}
