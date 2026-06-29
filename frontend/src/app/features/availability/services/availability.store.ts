import { DestroyRef, effect, inject, Injectable } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import { PropertyContextService } from '../../../shared/services/property-context.service';
import { ToastService } from '../../../shared/services/toast.service';
import { AvailabilityApiService } from './availability-api.service';
import { AvailabilityState } from './availability-state';
import { CalendarService } from '../components/availability-calendar/services/calendar.service';
import { SelectionService } from '../components/availability-quick-actions/services/selection.service';
import { InventoryService } from '../components/availability-data-tables/services/inventory.service';
import { BlackoutService } from '../components/availability-data-tables/services/blackout.service';
import { CellService } from '../components/availability-calendar/services/cell.service';
import { mapAvailability } from '../mappers/availability.mapper';
import type { AvailabilityDto } from '../models/availability.dto';

@Injectable()
export class AvailabilityStore {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly api = inject(AvailabilityApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastService);

  private readonly routePropId = toSignal(
    this.activatedRoute.queryParamMap.pipe(
      map((p) => Number(p.get('prop_id') ?? '0')),
      distinctUntilChanged(),
    ),
    { initialValue: 0 },
  );

  readonly state = new AvailabilityState(this.routePropId);
  readonly calendar = new CalendarService(this.state);
  readonly selection = new SelectionService(this.state, this.calendar, this.api, this.destroyRef, this.toast);
  readonly inventory = new InventoryService(this.state, this.calendar, this.api, this.destroyRef, this.toast, this.formBuilder);
  readonly blackout = new BlackoutService(this.state, this.calendar, this.api, this.destroyRef, this.toast, this.formBuilder);
  readonly cell = new CellService(this.state, this.calendar, this.inventory, this.blackout, this.toast);

  private readonly availabilityResource = httpResource<AvailabilityDto>(() => {
    const pid = this.routePropId();
    return pid > 0 ? `/api/management/availability?prop_id=${pid}&days=92` : undefined;
  });

  constructor() {
    effect(() => {
      const propId = this.routePropId();
      if (!propId) {
        this.state.viewState.set('empty');
        this.state.pageData.set(null);
        this.state.errorMessage.set('');
        this.state.submitMessage.set('');
        this.state.refreshing.set(false);
        this.propertyCtx.clear();
        return;
      }
      if (this.availabilityResource.isLoading()) {
        this.state.viewState.set(this.state.pageData() ? 'success' : 'loading');
        return;
      }
      if (this.availabilityResource.error()) {
        this.state.viewState.set('error');
        this.state.errorMessage.set('No se pudo cargar la información.');
        this.state.refreshing.set(false);
        return;
      }
      const dto = this.availabilityResource.value();
      if (dto) {
        const data = mapAvailability(dto);
        this.state.pageData.set(data);
        this.state.viewState.set('success');
        this.state.errorMessage.set('');
        this.propertyCtx.setProperty(data.propId, data.hotelName);
        this.calendar.rebuildCalendar();
        this._fetchHotelRooms(data.propId);
        this.state.refreshing.set(false);
        this.state.skeletonExiting.set(true);
        setTimeout(() => this.state.skeletonExiting.set(false), 300);
      }
    }, { allowSignalWrites: true });
  }

  // ── State signals ──

  get selectedPropId() { return this.state.selectedPropId; }
  get selectedLabel() { return this.state.selectedLabel; }
  get viewState() { return this.state.viewState; }
  get pageData() { return this.state.pageData; }
  get errorMessage() { return this.state.errorMessage; }
  get submitMessage() { return this.state.submitMessage; }
  get saving() { return this.state.saving; }
  get savingCell() { return this.state.savingCell; }
  get refreshing() { return this.state.refreshing; }
  get skeletonExiting() { return this.state.skeletonExiting; }
  get batchAvailableValue() { return this.state.batchAvailableValue; }
  get undoState() { return this.state.undoState; }
  get confirmAction() { return this.state.confirmAction; }
  get deleteConfirm() { return this.state.deleteConfirm; }
  get inventoryDeleteConfirm() { return this.state.inventoryDeleteConfirm; }
  get viewMode() { return this.state.viewMode; }
  get layoutMode() { return this.state.layoutMode; }
  get activeCell() { return this.state.activeCell; }
  get editingCell() { return this.state.editingCell; }
  get highlightedCell() { return this.state.highlightedCell; }
  get multiSelectMode() { return this.state.multiSelectMode; }
  get selectedCells() { return this.state.selectedCells; }
  get allHotelRooms() { return this.state.allHotelRooms; }
  get hotelRoomsForType() { return this.state.hotelRoomsForType; }
  get selectedAvailableRooms() { return this.state.selectedAvailableRooms; }
  get selectedBlockedRooms() { return this.state.selectedBlockedRooms; }
  get blackoutSelectedRooms() { return this.state.blackoutSelectedRooms; }
  get editingBlackout() { return this.state.editingBlackout; }
  get roomNumbersByType() { return this.state.roomNumbersByType; }
  get computedInventoryTotals() { return this.state.computedInventoryTotals; }

  // Calendar
  get displayCalendar() { return this.calendar.displayCalendar; }
  get skeletonCols() { return this.calendar.skeletonCols; }
  get avgOccupancy() { return this.calendar.avgOccupancy; }

  // Selection
  get selectionCount() { return this.selection.selectionCount; }
  get selectionSummary() { return this.selection.selectionSummary; }

  // Forms
  get inventoryForm() { return this.inventory.form; }
  get blackoutForm() { return this.blackout.form; }

  // ── Delegated methods ──

  onPropSelected(event: { propId: number; label: string }) {
    const pid = event.propId;
    if (!pid || pid === this.routePropId()) return;
    this.propertyCtx.setProperty(pid, event.label || `Propiedad #${pid}`);
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { prop_id: pid },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
    this.state.refreshing.set(true);
    this.state.errorMessage.set('');
    this.state.submitMessage.set('');
    this.state.undoState.set(null);
    if (this.state.undoTimer) { clearTimeout(this.state.undoTimer); this.state.undoTimer = null; }
    this.state.selectedCells.set(new Set());
    this.state.clearLastCellKey();
    this.state.activeCell.set(null);
    this.state.editingCell.set(null);
    this.state.savingCell.set(null);
  }

  setView = (m: 'month' | 'week') => this.calendar.setView(m);
  prevPeriod = () => this.calendar.prevPeriod();
  nextPeriod = () => this.calendar.nextPeriod();
  goToday = () => this.calendar.goToday();

  // Cell interaction
  onCellClick = (e: MouseEvent, d: string, r: string) => {
    if (this.state.multiSelectMode()) {
      if (e.shiftKey && this.state.hasLastCellKey()) this.selection.rangeSelect(d, r);
      else this.selection.toggleCell(d, r);
      this.state.lastCellKey = `${d}|${r}`;
    } else {
      this.cell.startEdit(d, r);
    }
  };

  startEdit = (d: string, r: string) => this.cell.startEdit(d, r);
  commitEdit = (d: string, r: string, el: HTMLInputElement | null) => this.cell.commitEdit(d, r, el);
  cancelEdit = () => this.cell.cancelEdit();
  isEditing = (d: string, r: string) => this.cell.isEditing(d, r);
  isSelected = (d: string, r: string) => this.cell.isSelected(d, r);
  isMultiSelected = (d: string, r: string) => this.state.selectedCells().has(`${d}|${r}`);

  // Quick actions
  quickBlock = () => this.cell.quickBlock();
  quickMarkUnavailable = () => this.cell.quickMarkUnavailable();

  // Selection
  toggleMultiSelect = (v: boolean) => this.selection.toggleMultiSelect(v);
  clearSelection = () => this.selection.clearSelection();
  selectAllCells = () => this.selection.selectAllCells();
  batchMarkUnavailable = () => this.selection.batchMarkUnavailable();
  blockSelectedRange = () => this.selection.blockSelectedRange();

  // Undo
  undoQuickAction() {
    const state = this.selection.undoQuickAction();
    if (!state) return;
    this.inventory.form.patchValue({
      roomTypeId: state.roomTypeId, date: state.date,
      totalRooms: state.totalRooms, availableRooms: state.availableRooms, blockedRooms: state.blockedRooms,
    });
    this.state.savingCell.set(`${state.date}|${state.roomTypeName}`);
    this.inventory.save();
    this.toast.info('Restaurando inventario anterior…');
  }

  dismissUndo = () => this.selection.dismissUndo();

  // Inventory
  onEditInventoryFromTable = (i: Parameters<InventoryService['onEditFromTable']>[0]) => this.inventory.onEditFromTable(i);
  onDeleteInventoryFromTable = (i: { date: string; roomTypeName: string }) => this.inventory.onDeleteFromTable(i);
  confirmDeleteInventory = () => this.inventory.confirmDelete();
  saveInventory = () => this.inventory.save();

  // Blackout
  onEditBlackout = (id: string) => this.blackout.onEdit(id);
  onDeleteBlackout = (id: string) => this.blackout.onDelete(id);
  confirmDeleteBlackout = () => this.blackout.confirmDelete();
  cancelEditBlackout = () => this.blackout.cancelEdit();
  saveBlackout = () => this.blackout.save();

  // Form helpers
  onInventoryRoomTypeChange = () => this.inventory.onRoomTypeChange();
  toggleInventoryRoom = (rn: string) => this.inventory.toggleRoom(rn);
  onBlackoutRoomTypeChange = () => this.blackout.onRoomTypeChange();
  toggleBlackoutRoom = (rn: string) => this.blackout.toggleRoom(rn);

  // Confirmation
  confirmAccept() {
    this.state.confirmAction()?.handler?.();
    this.state.confirmAction.set(null);
  }

  confirmCancel() { this.state.confirmAction.set(null); }

  // Keyboard
  handleEscape() {
    if (this.state.confirmAction()) this.confirmCancel();
    else if (this.state.editingCell()) this.cell.cancelEdit();
    else if (this.state.activeCell()) this.state.activeCell.set(null);
    else if (this.state.multiSelectMode()) this.selection.toggleMultiSelect(false);
  }

  navigateArrow(key: string) {
    const cal = this.calendar.displayCalendar();
    const vm = this.state.pageData();
    if (!cal || !vm || cal.days.length === 0 || vm.roomTypes.length === 0) return;

    const names = vm.roomTypes.map((r) => r.name);
    const current = this.state.activeCell();
    let di = current ? cal.days.findIndex((d) => d.date === current.date) : 0;
    let ri = current ? names.indexOf(current.roomTypeName) : 0;
    if (di < 0) di = 0;
    if (ri < 0) ri = 0;

    switch (key) {
      case 'ArrowLeft':  di = Math.max(0, di - 1); break;
      case 'ArrowRight': di = Math.min(cal.days.length - 1, di + 1); break;
      case 'ArrowUp':    ri = Math.max(0, ri - 1); break;
      case 'ArrowDown':  ri = Math.min(names.length - 1, ri + 1); break;
    }
    this.cell.startEdit(cal.days[di].date, names[ri]);
  }

  // ── Private ──

  private _fetchHotelRooms(propId: number) {
    if (!propId) { this.state.allHotelRooms.set([]); return; }
    this.api.getAllHotelRooms(propId).subscribe({
      next: (res) => {
        const rooms = (res.hotel_rooms || []).map((r) => ({
          hotelRoomId: r.hotel_room_id, roomNumber: r.room_number || '',
          roomLabel: r.room_label, roomTypeId: r.room_type_id,
          roomTypeName: r.room_type_name || '', floor: r.floor || '', isActive: r.is_active,
        }));
        console.log('[AvailabilityStore] getAllHotelRooms response:', rooms.length, 'rooms');
        if (rooms.length > 0) {
          console.log('[AvailabilityStore] sample room:', rooms[0]);
        }
        this.state.allHotelRooms.set(rooms);
      },
      error: (err) => {
        console.error('[AvailabilityStore] getAllHotelRooms error:', err);
        this.state.allHotelRooms.set([]);
      },
    });
  }
}
