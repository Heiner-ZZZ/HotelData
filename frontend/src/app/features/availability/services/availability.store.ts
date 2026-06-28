import { Injectable, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import type { ApiError } from '../../../core/api/api-error.model';
import { PropertyContextService } from '../../../shared/services/property-context.service';
import { ToastService } from '../../../shared/services/toast.service';
import type { ViewState } from '../../../shared/types/ui-state.type';
import type { AvailabilityViewModel, CalendarMonth, HotelRoomInfo } from '../models/availability.model';
import type { AvailabilityDto } from '../models/availability.dto';
import { AvailabilityApiService } from '../services/availability-api.service';
import { mapAvailability } from '../mappers/availability.mapper';
import { buildCalendarMonth, buildCalendarWeek, mondayOfWeek } from '../availability.helpers';
import type { ViewMode } from '../availability.helpers';

interface UndoState {
  date: string;
  roomTypeName: string;
  roomTypeId: string;
  totalRooms: number;
  availableRooms: number;
  blockedRooms: number;
}

@Injectable()
export class AvailabilityStore {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly api = inject(AvailabilityApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastService);

  // ── Route state ──

  private readonly routePropId = toSignal(
    this.activatedRoute.queryParamMap.pipe(
      map((params) => Number(params.get('prop_id') ?? '0')),
      distinctUntilChanged(),
    ),
    { initialValue: 0 },
  );

  readonly selectedPropId = computed(() => this.routePropId());

  // ── Data fetching ──

  private readonly availabilityResource = httpResource<AvailabilityDto>(() => {
    const propId = this.routePropId();
    return propId > 0 ? `/api/management/availability?prop_id=${propId}&days=92` : undefined;
  });

  readonly viewState = signal<ViewState>('loading');
  readonly pageData = signal<AvailabilityViewModel | null>(null);
  readonly errorMessage = signal('');
  readonly submitMessage = signal('');

  readonly selectedLabel = computed(() => this.pageData()?.hotelName ?? '');

  // ── Calendar state ──

  readonly viewMode = signal<ViewMode>('week');
  readonly calendarMonth = signal<CalendarMonth | null>(null);
  readonly calendarWeek = signal<CalendarMonth | null>(null);
  readonly calendarYear = signal(new Date().getFullYear());
  readonly calendarMonthIdx = signal(new Date().getMonth());
  readonly weekAnchor = signal<Date>(mondayOfWeek(new Date()));
  readonly activeCell = signal<{ date: string; roomTypeName: string } | null>(null);
  readonly editingCell = signal<{ date: string; roomTypeName: string } | null>(null);
  readonly layoutMode = signal<'scroll' | 'wrap'>('wrap');
  readonly today = new Date();

  // ── Multi-select state ──

  readonly multiSelectMode = signal(false);
  readonly selectedCells = signal<Set<string>>(new Set());
  private _lastCellKey = '';

  private _hasLastCell(): boolean {
    return this._lastCellKey !== '';
  }

  // ── Saving state ──

  readonly saving = signal(false);
  readonly savingCell = signal<string | null>(null);

  // ── Undo state ──

  readonly undoState = signal<UndoState | null>(null);
  private _undoTimer: ReturnType<typeof setTimeout> | null = null;

  // ── Confirmation state ──

  readonly confirmAction = signal<{ title: string; message: string; handler: () => void } | null>(null);
  readonly deleteConfirm = signal<{ blackoutId: string } | null>(null);
  readonly inventoryDeleteConfirm = signal<{ date: string; roomTypeName: string } | null>(null);

  // ── UI transient state ──

  readonly refreshing = signal(false);
  readonly skeletonExiting = signal(false);
  readonly highlightedCell = signal<{ key: string; label: string } | null>(null);
  private _highlightTimer: ReturnType<typeof setTimeout> | null = null;

  readonly batchAvailableValue = signal(0);

  // ── Hotel rooms state ──

  readonly allHotelRooms = signal<HotelRoomInfo[]>([]);
  readonly hotelRoomsForType = signal<
    Array<{ hotel_room_id: string; room_number: string; room_label: string; floor: string; is_active: boolean }>
  >([]);
  readonly selectedAvailableRooms = signal<Set<string>>(new Set());
  readonly selectedBlockedRooms = signal<Set<string>>(new Set());
  readonly blackoutSelectedRooms = signal<Set<string>>(new Set());
  readonly editingBlackout = signal<{
    blackoutId: string;
    roomTypeId: string;
    startDate: string;
    endDate: string;
    reason: string;
    roomNumbers: string[];
  } | null>(null);

  // ── Forms ──

  readonly inventoryForm = this.formBuilder.nonNullable.group({
    roomTypeId: ['', [Validators.required]],
    date: ['', [Validators.required]],
    totalRooms: [0, [Validators.required, Validators.min(0)]],
    availableRooms: [0, [Validators.required, Validators.min(0)]],
    blockedRooms: [0, [Validators.required, Validators.min(0)]],
  });

  readonly blackoutForm = this.formBuilder.nonNullable.group({
    roomTypeId: ['', [Validators.required]],
    startDate: ['', [Validators.required]],
    endDate: ['', [Validators.required]],
    blockedRooms: [0, [Validators.required, Validators.min(0)]],
    reason: [''],
  });

  // ── Computed ──

  readonly selectionCount = computed(() => this.selectedCells().size);

  readonly selectionGroups = computed(() => {
    const groups = new Map<string, { roomTypeName: string; dates: string[] }>();
    for (const key of this.selectedCells()) {
      const [date, roomTypeName] = key.split('|');
      if (!groups.has(roomTypeName)) {
        groups.set(roomTypeName, { roomTypeName, dates: [] });
      }
      groups.get(roomTypeName)!.dates.push(date);
    }
    return [...groups.values()];
  });

  readonly selectionSummary = computed(() => {
    const count = this.selectedCells().size;
    if (count === 0) return '';
    const groups = this.selectionGroups();
    if (groups.length === 1) {
      const g = groups[0];
      const sorted = [...g.dates].sort();
      const range = sorted.length > 1 ? `${sorted[0]} → ${sorted[sorted.length - 1]}` : sorted[0];
      return `${count} celdas · ${g.roomTypeName} · ${range}`;
    }
    return `${count} celdas · ${groups.length} tipo(s) de habitación`;
  });

  readonly displayCalendar = computed(() =>
    this.viewMode() === 'month' ? this.calendarMonth() : this.calendarWeek(),
  );

  readonly skeletonCols = computed(() => {
    const count =
      this.viewMode() === 'month'
        ? new Date(this.calendarYear(), this.calendarMonthIdx() + 1, 0).getDate()
        : 7;
    return Array.from({ length: count }, (_, i) => i + 1);
  });

  readonly avgOccupancy = computed(() => {
    const cal = this.displayCalendar();
    if (!cal) return 0;
    const daysWithData = cal.days.filter((d) => d.roomTypes.length > 0).length;
    if (daysWithData === 0) return 0;
    return (
      cal.days.reduce((sum, d) => {
        const pcts = d.roomTypes.map((r) => r.occupancyPct);
        return sum + (pcts.length > 0 ? pcts.reduce((a, b) => a + b, 0) / pcts.length : 0);
      }, 0) / daysWithData
    );
  });

  readonly roomNumbersByType = computed(() => {
    const rooms = this.allHotelRooms();
    const map = new Map<string, string[]>();
    for (const room of rooms) {
      const rtId = room.roomTypeId;
      if (!map.has(rtId)) map.set(rtId, []);
      if (room.roomNumber) map.get(rtId)!.push(room.roomNumber);
    }
    for (const [, nums] of map) {
      nums.sort((a, b) => {
        const na = parseInt(a, 10);
        const nb = parseInt(b, 10);
        if (!isNaN(na) && !isNaN(nb)) return na - nb;
        return a.localeCompare(b);
      });
    }
    return map;
  });

  readonly computedInventoryTotals = computed(() => {
    const available = this.selectedAvailableRooms();
    const blocked = this.selectedBlockedRooms();
    const total = available.size + blocked.size;
    return { total, available: available.size, blocked: blocked.size };
  });

  // ── Constructor: data sync effect ──

  constructor() {
    effect(() => {
      const propId = this.selectedPropId();

      if (!propId) {
        this.viewState.set('empty');
        this.pageData.set(null);
        this.errorMessage.set('');
        this.submitMessage.set('');
        this.refreshing.set(false);
        this.propertyCtx.clear();
        return;
      }

      if (this.availabilityResource.isLoading()) {
        this.viewState.set(this.pageData() ? 'success' : 'loading');
        return;
      }

      if (this.availabilityResource.error()) {
        this.viewState.set('error');
        this.errorMessage.set('No se pudo cargar la información.');
        this.refreshing.set(false);
        return;
      }

      const dto = this.availabilityResource.value();
      if (dto) {
        const data = mapAvailability(dto);
        this.pageData.set(data);
        this.viewState.set('success');
        this.errorMessage.set('');
        this.propertyCtx.setProperty(data.propId, data.hotelName);
        this._rebuildCalendar();
        this._fetchHotelRooms(data.propId);
        this.refreshing.set(false);
        this.skeletonExiting.set(true);
        setTimeout(() => this.skeletonExiting.set(false), 300);
      }
    }, { allowSignalWrites: true });
  }

  // ── Property selection ──

  onPropSelected(event: { propId: number; label: string }) {
    const propId = event.propId;
    if (!propId || propId === this.selectedPropId()) return;

    this.propertyCtx.setProperty(propId, event.label || `Propiedad #${propId}`);
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { prop_id: propId },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });

    this.refreshing.set(true);
    this.errorMessage.set('');
    this.submitMessage.set('');
    this.undoState.set(null);
    this._clearUndoTimer();
    this.selectedCells.set(new Set());
    this._lastCellKey = '';
    this.activeCell.set(null);
    this.editingCell.set(null);
    this.savingCell.set(null);
    this._clearHighlight();
  }

  // ── Calendar navigation ──

  setView(mode: ViewMode) {
    this.viewMode.set(mode);
    this._rebuildCalendar();
  }

  prevPeriod() {
    if (this.viewMode() === 'month') {
      const y = this.calendarYear();
      const m = this.calendarMonthIdx();
      if (m === 0) {
        this.calendarYear.set(y - 1);
        this.calendarMonthIdx.set(11);
      } else {
        this.calendarMonthIdx.set(m - 1);
      }
    } else {
      const anchor = new Date(this.weekAnchor());
      anchor.setDate(anchor.getDate() - 7);
      this.weekAnchor.set(anchor);
    }
    this.activeCell.set(null);
    this.editingCell.set(null);
    this._rebuildCalendar();
  }

  nextPeriod() {
    if (this.viewMode() === 'month') {
      const y = this.calendarYear();
      const m = this.calendarMonthIdx();
      if (m === 11) {
        this.calendarYear.set(y + 1);
        this.calendarMonthIdx.set(0);
      } else {
        this.calendarMonthIdx.set(m + 1);
      }
    } else {
      const anchor = new Date(this.weekAnchor());
      anchor.setDate(anchor.getDate() + 7);
      this.weekAnchor.set(anchor);
    }
    this.activeCell.set(null);
    this.editingCell.set(null);
    this._rebuildCalendar();
  }

  goToday() {
    this.calendarYear.set(this.today.getFullYear());
    this.calendarMonthIdx.set(this.today.getMonth());
    this.weekAnchor.set(mondayOfWeek(new Date()));
    this.activeCell.set(null);
    this.editingCell.set(null);
    this._rebuildCalendar();
  }

  // ── Cell interaction ──

  onCellClick(event: MouseEvent, date: string, roomTypeName: string) {
    if (this.multiSelectMode()) {
      if (event.shiftKey && this._lastCellKey) {
        this._rangeSelect(date, roomTypeName);
      } else {
        this._toggleCell(date, roomTypeName);
      }
      this._lastCellKey = `${date}|${roomTypeName}`;
    } else {
      this.startEdit(date, roomTypeName);
    }
  }

  toggleMultiSelect(enabled: boolean) {
    this.multiSelectMode.set(enabled);
    if (enabled) {
      this.activeCell.set(null);
      this.editingCell.set(null);
    } else {
      this.selectedCells.set(new Set());
      this._lastCellKey = '';
    }
  }

  isMultiSelected(date: string, roomTypeName: string): boolean {
    return this.selectedCells().has(`${date}|${roomTypeName}`);
  }

  clearSelection() {
    this.selectedCells.set(new Set());
    this._lastCellKey = '';
  }

  selectAllCells() {
    const cal = this.displayCalendar();
    const vm = this.pageData();
    if (!cal || !vm) return;

    const all = new Set<string>();
    for (const day of cal.days) {
      for (const rt of vm.roomTypes) {
        all.add(`${day.date}|${rt.name}`);
      }
    }
    this.selectedCells.set(all);
    if (all.size > 0) {
      const lastDay = cal.days[cal.days.length - 1];
      const lastRt = vm.roomTypes[vm.roomTypes.length - 1];
      this._lastCellKey = `${lastDay.date}|${lastRt.name}`;
    }
  }

  private _toggleCell(date: string, roomTypeName: string) {
    const key = `${date}|${roomTypeName}`;
    const current = this.selectedCells();
    const next = new Set(current);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    this.selectedCells.set(next);
  }

  private _rangeSelect(date: string, roomTypeName: string) {
    if (!this._hasLastCell()) {
      this._toggleCell(date, roomTypeName);
      return;
    }
    const [lastDate, lastName] = this._lastCellKey.split('|');
    if (lastName !== roomTypeName) {
      this._toggleCell(date, roomTypeName);
      return;
    }
    const cal = this.displayCalendar();
    if (!cal) return;

    const idxA = cal.days.findIndex((d) => d.date === lastDate);
    const idxB = cal.days.findIndex((d) => d.date === date);
    if (idxA === -1 || idxB === -1) return;

    const [start, end] = idxA < idxB ? [idxA, idxB] : [idxB, idxA];
    const current = this.selectedCells();
    const next = new Set(current);
    for (let i = start; i <= end; i++) {
      next.add(`${cal.days[i].date}|${roomTypeName}`);
    }
    this.selectedCells.set(next);
  }

  startEdit(date: string, roomTypeName: string) {
    const current = this.editingCell();
    if (current?.date === date && current?.roomTypeName === roomTypeName) return;

    this.activeCell.set({ date, roomTypeName });
    this.editingCell.set({ date, roomTypeName });

    const vm = this.pageData();
    const rt = vm?.roomTypes.find((r) => r.name === roomTypeName);
    const invItem = vm?.inventoryItems.find((i) => i.date === date && i.roomTypeName === roomTypeName);

    this.inventoryForm.patchValue({
      roomTypeId: rt?.id ?? roomTypeName,
      date,
      totalRooms: invItem?.totalRooms ?? 0,
      availableRooms: invItem?.availableRooms ?? 0,
      blockedRooms: invItem?.blockedRooms ?? 0,
    });

    this.onInventoryRoomTypeChange();

    setTimeout(() => {
      const input = document.querySelector<HTMLInputElement>('#cell-input-' + CSS.escape(date + roomTypeName));
      input?.focus();
      input?.select();
    }, 50);
  }

  commitEdit(date: string, roomTypeName: string, inputEl: HTMLInputElement | null) {
    const edit = this.editingCell();
    if (!edit || edit.date !== date || edit.roomTypeName !== roomTypeName) return;

    const raw = inputEl?.value ?? '';
    const val = parseInt(raw, 10);
    if (isNaN(val) || val < 0) {
      this.cancelEdit();
      return;
    }

    const vm = this.pageData();
    const invItem = vm?.inventoryItems.find((i) => i.date === date && i.roomTypeName === roomTypeName);
    const rt = vm?.roomTypes.find((r) => r.name === roomTypeName);
    const total = invItem?.totalRooms ?? 0;
    const clampedVal = Math.min(val, total);
    const blocked = total - clampedVal;

    this.inventoryForm.patchValue({
      roomTypeId: rt?.id ?? roomTypeName,
      date,
      totalRooms: total,
      availableRooms: clampedVal,
      blockedRooms: blocked,
    });

    this.savingCell.set(`${date}|${roomTypeName}`);
    this.editingCell.set(null);
    this.saveInventory();
  }

  cancelEdit() {
    this.editingCell.set(null);
    this.savingCell.set(null);
  }

  isEditing(date: string, roomTypeName: string): boolean {
    const edit = this.editingCell();
    return edit?.date === date && edit?.roomTypeName === roomTypeName;
  }

  isSelected(date: string, roomTypeName: string): boolean {
    const cell = this.activeCell();
    return cell?.date === date && cell?.roomTypeName === roomTypeName;
  }

  // ── Quick actions ──

  quickBlock() {
    const cell = this.activeCell();
    if (!cell) return;
    const vm = this.pageData();
    const rt = vm?.roomTypes.find((r) => r.name === cell.roomTypeName);

    this.blackoutForm.patchValue({
      roomTypeId: rt?.id ?? cell.roomTypeName,
      startDate: cell.date,
      endDate: cell.date,
      blockedRooms: 1,
      reason: 'Mantenimiento',
    });

    setTimeout(() => {
      const el = document.querySelector('.form-card:has(#blk-start)');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      (document.getElementById('blk-start') as HTMLInputElement)?.focus();
    }, 150);
  }

  quickMarkUnavailable() {
    const cell = this.activeCell();
    if (!cell) return;

    const vm = this.pageData();
    const invItem = vm?.inventoryItems.find((i) => i.date === cell.date && i.roomTypeName === cell.roomTypeName);
    const avail = invItem?.availableRooms ?? 0;
    const total = invItem?.totalRooms ?? 0;

    this.confirmAction.set({
      title: 'Marcar como no disponible',
      message: `Se establecerán 0 habitaciones disponibles para ${cell.roomTypeName} el ${cell.date} (actualmente ${avail} de ${total} disponibles). ¿Desea continuar?`,
      handler: () => this._executeQuickMarkUnavailable(),
    });
  }

  private _executeQuickMarkUnavailable() {
    const cell = this.activeCell();
    if (!cell) return;
    const vm = this.pageData();
    const invItem = vm?.inventoryItems.find((i) => i.date === cell.date && i.roomTypeName === cell.roomTypeName);
    const rt = vm?.roomTypes.find((r) => r.name === cell.roomTypeName);
    const total = invItem?.totalRooms ?? 1;

    this.undoState.set({
      date: cell.date,
      roomTypeName: cell.roomTypeName,
      roomTypeId: rt?.id ?? cell.roomTypeName,
      totalRooms: total,
      availableRooms: invItem?.availableRooms ?? 0,
      blockedRooms: invItem?.blockedRooms ?? 0,
    });

    this.inventoryForm.patchValue({
      roomTypeId: rt?.id ?? cell.roomTypeName,
      date: cell.date,
      totalRooms: total,
      availableRooms: 0,
      blockedRooms: total,
    });
    this.savingCell.set(`${cell.date}|${cell.roomTypeName}`);
    this.saveInventory();
  }

  // ── Batch operations ──

  batchMarkUnavailable() {
    const propId = this.selectedPropId();
    if (!propId) return;
    const vm = this.pageData();
    if (!vm) return;

    const cells: Array<{ date: string; roomTypeName: string; roomTypeId: string; totalRooms: number }> = [];
    for (const key of this.selectedCells()) {
      const [date, roomTypeName] = key.split('|');
      const invItem = vm.inventoryItems.find((i) => i.date === date && i.roomTypeName === roomTypeName);
      const rt = vm.roomTypes.find((r) => r.name === roomTypeName);
      cells.push({ date, roomTypeName, roomTypeId: rt?.id ?? roomTypeName, totalRooms: invItem?.totalRooms ?? 0 });
    }
    if (cells.length === 0) return;

    const targetAvail = Math.max(0, this.batchAvailableValue());
    this.saving.set(true);

    let completed = 0;
    const total = cells.length;

    for (const cell of cells) {
      const totalRooms = cell.totalRooms;
      const avail = Math.min(targetAvail, totalRooms);
      const blocked = totalRooms - avail;

      this.api
        .saveInventory({ prop_id: propId, room_type_id: cell.roomTypeId, date: cell.date, total_rooms: totalRooms, available_rooms: avail, blocked_rooms: blocked })
        .pipe(switchMap(() => this.api.getAvailability(propId, 92)), takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (data) => {
            completed++;
            this.pageData.set(data);
            const label = avail === 0 ? 'no disponible' : `${avail} disponibles`;
            this.toast.success(`${label} (${completed}/${total})`);
            this._rebuildCalendar();
            if (completed >= total) {
              this.selectedCells.set(new Set());
              this._lastCellKey = '';
              this.saving.set(false);
              this._clearHighlight();
              this.highlightedCell.set({ key: `${cell.date}|${cell.roomTypeName}`, label });
              this._highlightTimer = setTimeout(() => this.highlightedCell.set(null), 1200);
            }
          },
          error: (err: ApiError) => {
            this.toast.error(err.message || 'Error al actualizar disponibilidad.');
            this.saving.set(false);
          },
        });
    }
  }

  blockSelectedRange() {
    const propId = this.selectedPropId();
    if (!propId) return;
    const groups = this.selectionGroups();
    if (groups.length === 0) return;
    const vm = this.pageData();
    if (!vm) return;

    let completed = 0;
    const total = groups.length;
    this.saving.set(true);

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
            this.pageData.set(data);
            this.toast.success(`Bloqueo registrado (${completed}/${total})`);
            this._rebuildCalendar();
            if (completed >= total) {
              this.selectedCells.set(new Set());
              this._lastCellKey = '';
              this.saving.set(false);
            }
          },
          error: (err: ApiError) => {
            this.toast.error(err.message || 'Error al registrar bloqueo.');
            this.saving.set(false);
          },
        });
    }
  }

  // ── Inventory CRUD ──

  onEditInventoryFromTable(item: { date: string; roomTypeName: string; roomTypeId: string; totalRooms: number; availableRooms: number; blockedRooms: number }) {
    const vm = this.pageData();
    const rt = vm?.roomTypes.find((r) => r.name === item.roomTypeName);
    this.inventoryForm.patchValue({
      roomTypeId: rt?.id ?? item.roomTypeId,
      date: item.date,
      totalRooms: item.totalRooms,
      availableRooms: item.availableRooms,
      blockedRooms: item.blockedRooms,
    });
    this.onInventoryRoomTypeChange();
    setTimeout(() => {
      const el = document.getElementById('inventory-form-card');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);
  }

  onDeleteInventoryFromTable(item: { date: string; roomTypeName: string }) {
    this.inventoryDeleteConfirm.set({ date: item.date, roomTypeName: item.roomTypeName });
  }

  confirmDeleteInventory() {
    const payload = this.inventoryDeleteConfirm();
    if (!payload) return;
    this.inventoryDeleteConfirm.set(null);

    const propId = this.selectedPropId();
    if (!propId) return;
    const vm = this.pageData();
    const rt = vm?.roomTypes.find((r) => r.name === payload.roomTypeName);
    if (!rt) return;

    this.saving.set(true);
    this.api
      .deleteInventory(propId, rt.id, payload.date)
      .pipe(switchMap(() => this.api.getAvailability(propId, 92)), takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.pageData.set(data);
          this.toast.success('Registro de inventario eliminado');
          this._rebuildCalendar();
          this.saving.set(false);
        },
        error: (err: ApiError) => {
          this.toast.error(err.message || 'Error al eliminar registro de inventario.');
          this.saving.set(false);
        },
      });
  }

  saveInventory(): void {
    const propId = this.selectedPropId();
    if (!propId) {
      this.savingCell.set(null);
      return;
    }
    if (this.inventoryForm.invalid) {
      this.inventoryForm.markAllAsTouched();
      this.savingCell.set(null);
      return;
    }

    this.saving.set(true);
    const f = this.inventoryForm.controls;
    this.api
      .saveInventory({
        prop_id: propId,
        room_type_id: f.roomTypeId.value,
        date: f.date.value,
        total_rooms: f.totalRooms.value,
        available_rooms: f.availableRooms.value,
        blocked_rooms: f.blockedRooms.value,
      })
      .pipe(switchMap(() => this.api.getAvailability(propId, 92)), takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.pageData.set(data);
          this.toast.success('Inventario actualizado');
          this._rebuildCalendar();
          this.inventoryForm.reset({ roomTypeId: '', date: '', totalRooms: 0, availableRooms: 0, blockedRooms: 0 });
          this.activeCell.set(null);
          this.editingCell.set(null);
          this.hotelRoomsForType.set([]);
          this.selectedAvailableRooms.set(new Set());
          this.selectedBlockedRooms.set(new Set());

          const savedKey = this.savingCell();
          this.savingCell.set(null);
          if (savedKey) {
            this._clearHighlight();
            const [date, rtName] = savedKey.split('|');
            const inv = data.inventoryItems.find((i) => i.date === date && i.roomTypeName === rtName);
            this.highlightedCell.set({ key: savedKey, label: inv ? `${inv.availableRooms}/${inv.totalRooms} disponibles` : 'Actualizado' });
            this._highlightTimer = setTimeout(() => this.highlightedCell.set(null), 1200);
          }
          this.saving.set(false);

          if (this.undoState()) {
            this._clearUndoTimer();
            this._undoTimer = setTimeout(() => this.undoState.set(null), 10000);
          }
        },
        error: (err: ApiError) => {
          this.toast.error(err.message || 'Error al guardar inventario.');
          this.savingCell.set(null);
          this._clearHighlight();
          this.saving.set(false);
          this.undoState.set(null);
          this._clearUndoTimer();
        },
      });
  }

  // ── Blackout CRUD ──

  onEditBlackout(blackoutId: string) {
    const vm = this.pageData();
    if (!vm) return;
    const item = vm.blackoutItems.find((b) => b.blackoutId === blackoutId);
    if (!item) return;
    const [startDate, endDate] = item.rangeLabel.split(' -> ');

    this.blackoutForm.patchValue({
      roomTypeId: item.roomTypeId,
      startDate,
      endDate,
      blockedRooms: item.blockedRooms,
      reason: item.reason,
    });
    this.editingBlackout.set({
      blackoutId,
      roomTypeId: item.roomTypeId,
      startDate,
      endDate,
      reason: item.reason,
      roomNumbers: item.roomNumbers || [],
    });

    const propId = this.selectedPropId();
    if (propId && item.roomTypeId) {
      this.api.getHotelRooms(propId, item.roomTypeId).subscribe({
        next: (res) => {
          this.hotelRoomsForType.set(res.items);
          this.blackoutSelectedRooms.set(new Set(item.roomNumbers || []));
        },
        error: () => {},
      });
    }
    setTimeout(() => {
      const el = document.querySelector('.form-card:has(#blk-start)');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);
  }

  onDeleteBlackout(blackoutId: string) {
    this.deleteConfirm.set({ blackoutId });
  }

  confirmDeleteBlackout() {
    const payload = this.deleteConfirm();
    if (!payload) return;
    this.deleteConfirm.set(null);
    this.saving.set(true);

    this.api
      .deleteBlackout(payload.blackoutId)
      .pipe(switchMap(() => this.api.getAvailability(this.selectedPropId(), 92)), takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.pageData.set(data);
          this.toast.success('Bloqueo eliminado correctamente');
          this._rebuildCalendar();
          this.saving.set(false);
        },
        error: (err: ApiError) => {
          this.toast.error(err.message || 'Error al eliminar bloqueo.');
          this.saving.set(false);
        },
      });
  }

  cancelEditBlackout() {
    this.editingBlackout.set(null);
    this.blackoutForm.reset({ roomTypeId: '', startDate: '', endDate: '', blockedRooms: 0, reason: '' });
    this.blackoutSelectedRooms.set(new Set<string>());
  }

  saveBlackout(): void {
    const propId = this.selectedPropId();
    if (!propId || this.blackoutForm.invalid) {
      this.blackoutForm.markAllAsTouched();
      return;
    }

    const roomNumbers = [...this.blackoutSelectedRooms()];
    if (roomNumbers.length > 0) {
      this.blackoutForm.patchValue({ blockedRooms: roomNumbers.length });
    }

    this.saving.set(true);
    const editing = this.editingBlackout();
    const payload: Record<string, unknown> = {
      prop_id: propId,
      room_type_id: this.blackoutForm.controls.roomTypeId.value,
      start_date: this.blackoutForm.controls.startDate.value,
      end_date: this.blackoutForm.controls.endDate.value,
      reason: this.blackoutForm.controls.reason.value,
    };
    if (roomNumbers.length > 0) payload['room_numbers'] = roomNumbers;
    else payload['blocked_rooms'] = this.blackoutForm.controls.blockedRooms.value;

    const request$ = editing ? this.api.updateBlackout(editing.blackoutId, payload) : this.api.createBlackout(payload as any);

    request$
      .pipe(switchMap(() => this.api.getAvailability(propId, 92)), takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (data) => {
          this.pageData.set(data);
          this.toast.success('Bloqueo registrado');
          this._rebuildCalendar();
          this.blackoutForm.reset({ roomTypeId: '', startDate: '', endDate: '', blockedRooms: 0, reason: '' });
          this.editingBlackout.set(null);
          this.blackoutSelectedRooms.set(new Set());
          this.hotelRoomsForType.set([]);
          this.saving.set(false);
        },
        error: (err: ApiError) => {
          this.toast.error(err.message || 'Error al registrar bloqueo.');
          this.saving.set(false);
        },
      });
  }

  // ── Inventory form helpers ──

  onInventoryRoomTypeChange() {
    const roomTypeId = this.inventoryForm.controls.roomTypeId.value;
    const propId = this.selectedPropId();
    if (!roomTypeId || !propId) {
      this.hotelRoomsForType.set([]);
      this.selectedAvailableRooms.set(new Set());
      this.selectedBlockedRooms.set(new Set());
      return;
    }
    this.api.getHotelRooms(propId, roomTypeId).subscribe({
      next: (res) => {
        this.hotelRoomsForType.set(res.items);
        this.selectedAvailableRooms.set(new Set(res.items.map((r) => r.room_number)));
        this.selectedBlockedRooms.set(new Set());
        this._syncInventoryFormFromCheckboxes();
      },
      error: () => this.hotelRoomsForType.set([]),
    });
  }

  toggleInventoryRoom(roomNumber: string) {
    const available = new Set(this.selectedAvailableRooms());
    const blocked = new Set(this.selectedBlockedRooms());
    if (available.has(roomNumber)) {
      available.delete(roomNumber);
      blocked.add(roomNumber);
    } else if (blocked.has(roomNumber)) {
      blocked.delete(roomNumber);
      available.add(roomNumber);
    } else {
      available.add(roomNumber);
    }
    this.selectedAvailableRooms.set(available);
    this.selectedBlockedRooms.set(blocked);
    this._syncInventoryFormFromCheckboxes();
  }

  toggleBlackoutRoom(roomNumber: string) {
    const selected = new Set(this.blackoutSelectedRooms());
    if (selected.has(roomNumber)) selected.delete(roomNumber);
    else selected.add(roomNumber);
    this.blackoutSelectedRooms.set(selected);
  }

  onBlackoutRoomTypeChange() {
    const roomTypeId = this.blackoutForm.controls.roomTypeId.value;
    const propId = this.selectedPropId();
    if (!roomTypeId || !propId) {
      this.blackoutSelectedRooms.set(new Set());
      return;
    }
    this.api.getHotelRooms(propId, roomTypeId).subscribe({
      next: (res) => {
        this.hotelRoomsForType.set(res.items);
        this.blackoutSelectedRooms.set(new Set());
      },
      error: () => {},
    });
  }

  // ── Confirmation ──

  confirmAccept() {
    const handler = this.confirmAction()?.handler;
    this.confirmAction.set(null);
    if (handler) handler();
  }

  confirmCancel() {
    this.confirmAction.set(null);
  }

  // ── Undo ──

  undoQuickAction() {
    const state = this.undoState();
    if (!state) return;
    this.undoState.set(null);
    this._clearUndoTimer();
    this.inventoryForm.patchValue({
      roomTypeId: state.roomTypeId, date: state.date,
      totalRooms: state.totalRooms, availableRooms: state.availableRooms, blockedRooms: state.blockedRooms,
    });
    this.savingCell.set(`${state.date}|${state.roomTypeName}`);
    this.saveInventory();
    this.toast.info('Restaurando inventario anterior…');
  }

  dismissUndo() {
    this.undoState.set(null);
    this._clearUndoTimer();
  }

  // ── Keyboard ──

  handleEscape() {
    if (this.confirmAction()) this.confirmCancel();
    else if (this.editingCell()) this.cancelEdit();
    else if (this.activeCell()) this.activeCell.set(null);
    else if (this.multiSelectMode()) this.toggleMultiSelect(false);
  }

  navigateArrow(key: string) {
    const cal = this.displayCalendar();
    const vm = this.pageData();
    if (!cal || !vm || cal.days.length === 0 || vm.roomTypes.length === 0) return;

    const roomTypeNames = vm.roomTypes.map((r) => r.name);
    const current = this.activeCell();
    let dayIdx = current ? cal.days.findIndex((d) => d.date === current.date) : 0;
    let rtIdx = current ? roomTypeNames.indexOf(current.roomTypeName) : 0;
    if (dayIdx < 0) dayIdx = 0;
    if (rtIdx < 0) rtIdx = 0;

    switch (key) {
      case 'ArrowLeft':  dayIdx = Math.max(0, dayIdx - 1); break;
      case 'ArrowRight': dayIdx = Math.min(cal.days.length - 1, dayIdx + 1); break;
      case 'ArrowUp':    rtIdx = Math.max(0, rtIdx - 1); break;
      case 'ArrowDown':  rtIdx = Math.min(roomTypeNames.length - 1, rtIdx + 1); break;
    }
    this.startEdit(cal.days[dayIdx].date, roomTypeNames[rtIdx]);
  }

  // ── Private helpers ──

  private _fetchHotelRooms(propId: number) {
    if (!propId) {
      this.allHotelRooms.set([]);
      return;
    }
    this.api.getAllHotelRooms(propId).subscribe({
      next: (res) => {
        this.allHotelRooms.set(
          (res.hotel_rooms || []).map((r) => ({
            hotelRoomId: r.hotel_room_id,
            roomNumber: r.room_number || '',
            roomLabel: r.room_label,
            roomTypeId: r.room_type_id,
            roomTypeName: r.room_type_name || '',
            floor: r.floor || '',
            isActive: r.is_active,
          })),
        );
      },
      error: () => this.allHotelRooms.set([]),
    });
  }

  private _rebuildCalendar() {
    const vm = this.pageData();
    if (!vm) return;
    if (this.viewMode() === 'month') {
      this.calendarMonth.set(buildCalendarMonth(this.calendarYear(), this.calendarMonthIdx(), vm.inventoryItems));
    } else {
      this.calendarWeek.set(buildCalendarWeek(this.weekAnchor(), vm.inventoryItems));
    }
  }

  private _syncInventoryFormFromCheckboxes() {
    const totals = this.computedInventoryTotals();
    this.inventoryForm.patchValue({
      totalRooms: totals.total,
      availableRooms: totals.available,
      blockedRooms: totals.blocked,
    });
  }

  private _clearUndoTimer() {
    if (this._undoTimer) { clearTimeout(this._undoTimer); this._undoTimer = null; }
  }

  private _clearHighlight() {
    if (this._highlightTimer) { clearTimeout(this._highlightTimer); this._highlightTimer = null; }
    this.highlightedCell.set(null);
  }
}
