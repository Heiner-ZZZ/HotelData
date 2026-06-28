import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, HostListener, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { ToastService } from '../../../../shared/services/toast.service';
import { AvailabilityCalendarComponent } from '../../components/availability-calendar/availability-calendar';
import { AvailabilityQuickActionsComponent } from '../../components/availability-quick-actions/availability-quick-actions';
import { AvailabilityDataTablesComponent } from '../../components/availability-data-tables/availability-data-tables';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { AvailabilityInventoryItem, AvailabilityViewModel, CalendarMonth, CalendarRoomTypeCell, HotelRoomInfo } from '../../models/availability.model';
import type { AvailabilityDto } from '../../models/availability.dto';
import { AvailabilityApiService } from '../../services/availability-api.service';
import { mapAvailability } from '../../mappers/availability.mapper';

/** Snapshot of cell state before a quick action, so we can undo. */
interface UndoState {
  date: string;
  roomTypeName: string;
  roomTypeId: string;
  totalRooms: number;
  availableRooms: number;
  blockedRooms: number;
}

const MONTH_NAMES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
];

const DAY_NAMES = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];

/** Return the timestamp of the Monday anchoring the week containing this date. */
function _weekMonday(date: Date): number {
  return mondayOfWeek(date).getTime();
}

type ViewMode = 'month' | 'week';

/** Shared: group inventory items by date */
function _groupByDate(items: AvailabilityInventoryItem[]): Map<string, AvailabilityInventoryItem[]> {
  const byDate = new Map<string, AvailabilityInventoryItem[]>();
  for (const item of items) {
    const dateStr = item.date;
    if (!byDate.has(dateStr)) byDate.set(dateStr, []);
    byDate.get(dateStr)!.push(item);
  }
  return byDate;
}

/** Shared: build CalendarRoomTypeCell[] for a given date */
function _roomTypesForDate(byDate: Map<string, AvailabilityInventoryItem[]>, dateStr: string): CalendarRoomTypeCell[] {
  return (byDate.get(dateStr) ?? []).map((inv) => ({
    roomTypeId: inv.roomTypeName,
    roomTypeName: inv.roomTypeName,
    totalRooms: inv.totalRooms,
    availableRooms: inv.availableRooms,
    blockedRooms: inv.blockedRooms,
    occupancyPct: inv.occupancyPct,
  }));
}

/** Build a full month view */
function buildCalendarMonth(year: number, month: number, items: AvailabilityInventoryItem[]): CalendarMonth {
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const today = new Date();
  const todayStr = today.toISOString().slice(0, 10);
  const byDate = _groupByDate(items);

  const currentWeekMonday = _weekMonday(today);

  const days: CalendarMonth['days'] = [];
  for (let d = 1; d <= daysInMonth; d++) {
    const dateObj = new Date(year, month, d);
    const dateStr = dateObj.toISOString().slice(0, 10);
    const dayOfWeek = dateObj.getDay();

    days.push({
      date: dateStr,
      day: d,
      dayName: DAY_NAMES[dayOfWeek],
      isToday: dateStr === todayStr,
      isWeekend: dayOfWeek === 0 || dayOfWeek === 6,
      isPast: dateStr < todayStr,
      isCurrentWeek: _weekMonday(dateObj) === currentWeekMonday,
      roomTypes: _roomTypesForDate(byDate, dateStr),
    });
  }

  return {
    year,
    month,
    monthName: MONTH_NAMES[month],
    days,
  };
}

/** Build a single-week (7-day) view starting from a Monday anchor date.
 *  The anchor is a Monday at 00:00:00 UTC; we build 7 consecutive days. */
function buildCalendarWeek(anchorMonday: Date, items: AvailabilityInventoryItem[]): CalendarMonth {
  const today = new Date();
  const todayStr = today.toISOString().slice(0, 10);
  const byDate = _groupByDate(items);

  // anchorMonday is a Monday; build 7 days: Mon -> Sun
  const days: CalendarMonth['days'] = [];
  for (let i = 0; i < 7; i++) {
    const dateObj = new Date(anchorMonday);
    dateObj.setDate(anchorMonday.getDate() + i);
    const dateStr = dateObj.toISOString().slice(0, 10);
    const dayOfWeek = dateObj.getDay();

    days.push({
      date: dateStr,
      day: dateObj.getDate(),
      dayName: DAY_NAMES[dayOfWeek],
      isToday: dateStr === todayStr,
      isWeekend: dayOfWeek === 0 || dayOfWeek === 6,
      isPast: dateStr < todayStr,
      isCurrentWeek: true, // always true in week view; the whole view is the current week
      roomTypes: _roomTypesForDate(byDate, dateStr),
    });
  }

  const month = anchorMonday.getMonth();
  return {
    year: anchorMonday.getFullYear(),
    month,
    monthName: MONTH_NAMES[month],
    days,
  };
}

/** Return the Monday of the week containing the given date. */
function mondayOfWeek(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay(); // 0=Sun .. 6=Sat
  const diff = day === 0 ? -6 : 1 - day; // Monday = 1
  d.setDate(d.getDate() + diff);
  d.setHours(0, 0, 0, 0);
  return d;
}

@Component({
  selector: 'app-availability-page',
  imports: [
    AvailabilityCalendarComponent,
    AvailabilityDataTablesComponent,
    AvailabilityQuickActionsComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    PropertySelectorComponent,
    ReactiveFormsModule,
  ],
  templateUrl: './availability-page.html',
  styleUrl: './availability-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AvailabilityPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly api = inject(AvailabilityApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastService);

  /** Prop ID from route query params — source of truth for current selection. */
  private readonly routePropId = toSignal(
    this.activatedRoute.queryParamMap.pipe(
      map((params) => Number(params.get('prop_id') ?? '0')),
      distinctUntilChanged(),
    ),
    { initialValue: 0 }
  );

  /** Declarative data fetching — auto-fetches when routePropId changes. */
  private readonly availabilityResource = httpResource<AvailabilityDto>(() => {
    const propId = this.routePropId();
    return propId > 0 ? `/api/management/availability?prop_id=${propId}&days=92` : undefined;
  });

  readonly viewState = signal<ViewState>('loading');
  readonly pageData = signal<AvailabilityViewModel | null>(null);
  /** @deprecated Use toast service instead - kept for legacy compatibility */
  readonly errorMessage = signal('');
  /** @deprecated Use toast service instead - kept for legacy compatibility */
  readonly submitMessage = signal('');

  /** Current property ID — derived from URL (source of truth). */
  readonly selectedPropId = computed(() => this.routePropId());

  /** Current property name — derived from loaded data. */
  readonly selectedLabel = computed(() => this.pageData()?.hotelName ?? '');

  // Calendar state
  readonly viewMode = signal<ViewMode>('week');
  readonly calendarMonth = signal<CalendarMonth | null>(null);
  readonly calendarWeek = signal<CalendarMonth | null>(null);
  readonly calendarYear = signal(new Date().getFullYear());
  readonly calendarMonthIdx = signal(new Date().getMonth());
  readonly weekAnchor = signal<Date>(mondayOfWeek(new Date())); // Monday of current week
  readonly activeCell = signal<{ date: string; roomTypeName: string } | null>(null);
  /** Inline editing state — which cell is currently being edited in-place. */
  readonly editingCell = signal<{ date: string; roomTypeName: string } | null>(null);

  /** Multi-select mode for blocking date ranges. */
  readonly multiSelectMode = signal(false);
  /** Set of "date|roomTypeName" keys for multi-selected cells. */
  readonly selectedCells = signal<Set<string>>(new Set());
  /** Last clicked cell (for Shift+range selection in the same room type row). */
  private _lastCellKey = '';

  /** Whether any save/block operation is in progress — disables buttons + shows spinner. */
  readonly saving = signal(false);

  /** Tracks which cell was inline-edited and is currently being saved ("date|roomTypeName").
   *  While non-null, that cell shows a spinner instead of the static value. */
  readonly savingCell = signal<string | null>(null);

  /** Undo state for quick actions — allows restoring previous inventory values. */
  readonly undoState = signal<UndoState | null>(null);
  private _undoTimer: ReturnType<typeof setTimeout> | null = null;

  /** Confirmation dialog state for destructive quick actions. */
  readonly confirmAction = signal<{
    title: string;
    message: string;
    handler: () => void;
  } | null>(null);

  /** Confirmation dialog for blackout deletion. */
  readonly deleteConfirm = signal<{ blackoutId: string } | null>(null);

  /** Confirmation dialog for inventory deletion. */
  readonly inventoryDeleteConfirm = signal<{ date: string; roomTypeName: string } | null>(null);

  /** Whether the calendar is refreshing due to property switch — shows skeleton loader. */
  readonly refreshing = signal(false);
  /** Tracks the skeleton exit animation phase — when true, skeleton fades out while content fades in. */
  readonly skeletonExiting = signal(false);

  /** Cell that was just saved — shows a brief green flash + floating tooltip with the new value. */
  readonly highlightedCell = signal<{ key: string; label: string } | null>(null);
  private _highlightTimer: ReturnType<typeof setTimeout> | null = null;

  /** Calendar layout mode: scroll (horizontal) or wrap (multi-row weeks). */
  readonly layoutMode = signal<'scroll' | 'wrap'>('wrap');

  /** Desired number of available rooms for the batch mark-unavailable action. */
  readonly batchAvailableValue = signal(0);

  /** Keyboard shortcut: listen for keydown at the document level. */
  @HostListener('document:keydown', ['$event'])
  handleKeyboard(event: KeyboardEvent) {
    const tag = (event.target as HTMLElement)?.tagName;
    const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';

    // ── Escape ──
    if (event.key === 'Escape') {
      if (isInput) return; // don't interfere with form inputs / inline editor
      event.preventDefault();
      this._handleEscape();
      return;
    }

    // ── Arrow keys: only navigate when NOT focused on an input field ──
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
      if (isInput || this.multiSelectMode() || this.saving()) return;
      event.preventDefault();
      this._navigateArrow(event.key);
    }
  }


  /** Count of currently multi-selected cells. */
  readonly selectionCount = computed(() => this.selectedCells().size);

  /** Derived info about multi-selection grouped by room type. */
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

  /** Compute a summary label for the multi-selection. */
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

  /** The currently displayed calendar data (month or week). */
  readonly displayCalendar = computed(() =>
    this.viewMode() === 'month' ? this.calendarMonth() : this.calendarWeek()
  );

  /** Number of skeleton columns (days in month for month view, 7 for week view). */
  readonly skeletonCols = computed(() => {
    const count = this.viewMode() === 'month'
      ? new Date(this.calendarYear(), this.calendarMonthIdx() + 1, 0).getDate()
      : 7;
    return Array.from({ length: count }, (_, i) => i + 1);
  });

  /** Average occupancy percentage across all visible days in the current calendar view. */
  readonly avgOccupancy = computed(() => {
    const cal = this.displayCalendar();
    if (!cal) return 0;
    const daysWithData = cal.days.filter(d => d.roomTypes.length > 0).length;
    if (daysWithData === 0) return 0;
    return cal.days.reduce((sum, d) => {
      const pcts = d.roomTypes.map(r => r.occupancyPct);
      return sum + (pcts.length > 0 ? pcts.reduce((a, b) => a + b, 0) / pcts.length : 0);
    }, 0) / daysWithData;
  });

  /** All hotel rooms for the property (for calendar room-number display). */
  readonly allHotelRooms = signal<HotelRoomInfo[]>([]);

  /** Map of room type ID → room numbers for display in calendar row headers. */
  readonly roomNumbersByType = computed(() => {
    const rooms = this.allHotelRooms();
    const map = new Map<string, string[]>();
    for (const room of rooms) {
      const rtId = room.roomTypeId;
      if (!map.has(rtId)) map.set(rtId, []);
      if (room.roomNumber) map.get(rtId)!.push(room.roomNumber);
    }
    // Sort room numbers numerically
    for (const [key, nums] of map) {
      nums.sort((a, b) => {
        const na = parseInt(a, 10);
        const nb = parseInt(b, 10);
        if (!isNaN(na) && !isNaN(nb)) return na - nb;
        return a.localeCompare(b);
      });
      map.set(key, nums);
    }
    return map;
  });

  /** Rooms fetched for the selected room type (multi-select). */
  readonly hotelRoomsForType = signal<Array<{ hotel_room_id: string; room_number: string; room_label: string; floor: string; is_active: boolean }>>([]);
  /** Set of room numbers selected as 'available' in the inventory form. */
  readonly selectedAvailableRooms = signal<Set<string>>(new Set());
  /** Set of room numbers selected as 'blocked' in the inventory form. */
  readonly selectedBlockedRooms = signal<Set<string>>(new Set());

  /** For blackout: set of room numbers selected to block. */
  readonly blackoutSelectedRooms = signal<Set<string>>(new Set());
  /** Blackout being edited (null = creating new). */
  readonly editingBlackout = signal<{
    blackoutId: string;
    roomTypeId: string;
    startDate: string;
    endDate: string;
    reason: string;
    roomNumbers: string[];
  } | null>(null);

  /** Fetch all hotel rooms when prop ID changes (for calendar room-number display). */
  private _fetchHotelRooms(propId: number) {
    if (!propId) {
      this.allHotelRooms.set([]);
      return;
    }
    this.api.getAllHotelRooms(propId).subscribe({
      next: (res) => {
        const rooms: HotelRoomInfo[] = (res.hotel_rooms || []).map(r => ({
          hotelRoomId: r.hotel_room_id,
          roomNumber: r.room_number || '',
          roomLabel: r.room_label,
          roomTypeId: r.room_type_id,
          roomTypeName: r.room_type_name || '',
          floor: r.floor || '',
          isActive: r.is_active,
        }));
        this.allHotelRooms.set(rooms);
      },
      error: () => this.allHotelRooms.set([]),
    });
  }

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

  /** Computed: auto-calculate totals from selected rooms. */
  readonly computedInventoryTotals = computed(() => {
    const available = this.selectedAvailableRooms();
    const blocked = this.selectedBlockedRooms();
    const total = available.size + blocked.size;
    return { total, available: available.size, blocked: blocked.size };
  });

  /** Fetch hotel rooms when room type changes in inventory form. */
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
        // Pre-populate: all rooms as available by default
        this.selectedAvailableRooms.set(new Set(res.items.map(r => r.room_number)));
        this.selectedBlockedRooms.set(new Set());
        // Sync form totals from checkbox state
        this._syncInventoryFormFromCheckboxes();
      },
      error: () => this.hotelRoomsForType.set([]),
    });
  }

  /** Toggle a room between available/blocked in inventory form. */
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
    // Sync form totals whenever checkboxes change
    this._syncInventoryFormFromCheckboxes();
  }

  /** Toggle a room for blackout multi-select. */
  toggleBlackoutRoom(roomNumber: string) {
    const selected = new Set(this.blackoutSelectedRooms());
    if (selected.has(roomNumber)) {
      selected.delete(roomNumber);
    } else {
      selected.add(roomNumber);
    }
    this.blackoutSelectedRooms.set(selected);
  }

  /** Fetch hotel rooms when room type changes in blackout form. */
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

  readonly today = new Date();

  constructor() {
    // ── Sync httpResource → pageData + viewState ──
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
        // Fetch hotel rooms for calendar room-number display
        this._fetchHotelRooms(data.propId);
        this.refreshing.set(false);
        this.skeletonExiting.set(true);
        setTimeout(() => this.skeletonExiting.set(false), 300);
      }
    }, { allowSignalWrites: true });
  }

  /** Switch to a different property without a full page reload.
   *  Fetches fresh data directly and updates all signals in-place.
   *  Shows a skeleton loader on the calendar while loading. */
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

  /** Set view mode (month or week) */
  setView(mode: ViewMode) {
    this.viewMode.set(mode);
    this._rebuildCalendar();
  }

  /** Navigate backward (previous month or previous week) */
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

  /** Navigate forward (next month or next week) */
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

  /** Go back to today (current month or current week) */
  goToday() {
    this.calendarYear.set(this.today.getFullYear());
    this.calendarMonthIdx.set(this.today.getMonth());
    this.weekAnchor.set(mondayOfWeek(new Date()));
    this.activeCell.set(null);
    this.editingCell.set(null);
    this._rebuildCalendar();
  }

  /** Handle click on a calendar cell — enter inline edit mode so user types value before saving. */
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

  /** Toggle multi-select mode on/off, clearing selection/reset state when turning off. */
  toggleMultiSelect(enabled: boolean) {
    this.multiSelectMode.set(enabled);
    if (enabled) {
      this.activeCell.set(null); // prevent visual conflict with cell-selected styling
      this.editingCell.set(null);
    } else {
      this.selectedCells.set(new Set());
      this._lastCellKey = '';
    }
  }

  /** Check if a cell is in the multi-selected set. */
  isMultiSelected(date: string, roomTypeName: string): boolean {
    return this.selectedCells().has(`${date}|${roomTypeName}`);
  }

  /** Clear all multi-selected cells. */
  clearSelection() {
    this.selectedCells.set(new Set());
    this._lastCellKey = '';
  }

  /** Select every visible cell in the current calendar display. */
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
    // Set _lastCellKey so shift-click range selection works from the last cell
    if (all.size > 0) {
      const lastDay = cal.days[cal.days.length - 1];
      const lastRt = vm.roomTypes[vm.roomTypes.length - 1];
      this._lastCellKey = `${lastDay.date}|${lastRt.name}`;
    }
  }

  /** Guard: shift-click with no prior cell falls back to toggle. */
  private _hasLastCell(): boolean {
    return this._lastCellKey !== '';
  }

  /** Mark all selected cells with a custom available-room count in batch.
   *  One API call per cell, then refreshes. */
  batchMarkUnavailable() {
    const propId = this.selectedPropId();
    if (!propId) return;

    const vm = this.pageData();
    if (!vm) return;

    // Flatten selection into individual cells
    const cells: Array<{ date: string; roomTypeName: string; roomTypeId: string; totalRooms: number }> = [];
    for (const key of this.selectedCells()) {
      const [date, roomTypeName] = key.split('|');
      const invItem = vm.inventoryItems.find(
        (i) => i.date === date && i.roomTypeName === roomTypeName
      );
      const rt = vm.roomTypes.find((r) => r.name === roomTypeName);
      cells.push({
        date,
        roomTypeName,
        roomTypeId: rt?.id ?? roomTypeName,
        totalRooms: invItem?.totalRooms ?? 0,
      });
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
        .saveInventory({
          prop_id: propId,
          room_type_id: cell.roomTypeId,
          date: cell.date,
          total_rooms: totalRooms,
          available_rooms: avail,
          blocked_rooms: blocked,
        })
        .pipe(
          switchMap(() => this.api.getAvailability(propId, 92)),
          takeUntilDestroyed(this.destroyRef),
        )
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

              // Highlight the last completed cell
              const cellKey = `${cell.date}|${cell.roomTypeName}`;
              this._clearHighlight();
              this.highlightedCell.set({ key: cellKey, label });
              this._highlightTimer = setTimeout(() => {
                this.highlightedCell.set(null);
              }, 1200);
            }
          },
          error: (err: ApiError) => {
            this.toast.error(err.message || 'Error al actualizar disponibilidad.');
            this.saving.set(false);
          },
        });
    }
  }

  /** Block all selected date ranges: one API call per room type group. */
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
        .pipe(
          switchMap(() => this.api.getAvailability(propId, 92)),
          takeUntilDestroyed(this.destroyRef),
        )
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

  /** Click on a calendar cell — enter inline edit mode (user types value, then presses Enter to save). */
  startEdit(date: string, roomTypeName: string) {
    // Skip if already editing this cell
    const current = this.editingCell();
    if (current?.date === date && current?.roomTypeName === roomTypeName) return;

    this.activeCell.set({ date, roomTypeName });
    this.editingCell.set({ date, roomTypeName });

    // Find the room type id that matches this name
    const vm = this.pageData();
    const rt = vm?.roomTypes.find((r) => r.name === roomTypeName);
    const invItem = vm?.inventoryItems.find(
      (i) => i.date === date && i.roomTypeName === roomTypeName
    );

    const rtId = rt?.id ?? roomTypeName;
    this.inventoryForm.patchValue({
      roomTypeId: rtId,
      date,
      totalRooms: invItem?.totalRooms ?? 0,
      availableRooms: invItem?.availableRooms ?? 0,
      blockedRooms: invItem?.blockedRooms ?? 0,
    });

    // Load hotel rooms for the selected room type so the form shows room checkboxes
    this.onInventoryRoomTypeChange();

    // Auto-focus the inline input after render
    setTimeout(() => {
      const input = document.querySelector<HTMLInputElement>('#cell-input-' + CSS.escape(date + roomTypeName));
      input?.focus();
      input?.select();
    }, 50);
  }

  // ── Private multi-select helpers ──

  private _toggleCell(date: string, roomTypeName: string) {
    const key = `${date}|${roomTypeName}`;
    const current = this.selectedCells();
    const next = new Set(current);
    if (next.has(key)) {
      next.delete(key);
    } else {
      next.add(key);
    }
    this.selectedCells.set(next);
  }

  private _rangeSelect(date: string, roomTypeName: string) {
    if (!this._hasLastCell()) {
      this._toggleCell(date, roomTypeName);
      return;
    }
    const [lastDate, lastName] = this._lastCellKey.split('|');
    if (lastName !== roomTypeName) {
      // Different room type — just toggle the clicked cell
      this._toggleCell(date, roomTypeName);
      return;
    }
    // Same room type: find all display-calendar days between the two dates
    const cal = this.displayCalendar();
    if (!cal) return;

    const idxA = cal.days.findIndex((d) => d.date === lastDate);
    const idxB = cal.days.findIndex((d) => d.date === date);
    if (idxA === -1 || idxB === -1) return;

    const [start, end] = idxA < idxB ? [idxA, idxB] : [idxB, idxA];
    const current = this.selectedCells();
    const next = new Set(current);
    // Add all cells in the range for this room type
    for (let i = start; i <= end; i++) {
      next.add(`${cal.days[i].date}|${roomTypeName}`);
    }
    this.selectedCells.set(next);
  }

  /** Commit inline edit: save the new available rooms value */
  commitEdit(date: string, roomTypeName: string, inputEl: HTMLInputElement | null) {
    const edit = this.editingCell();
    // Ignore if no longer editing this cell (user may have clicked another)
    if (!edit || edit.date !== date || edit.roomTypeName !== roomTypeName) return;

    const raw = inputEl?.value ?? '';
    const val = parseInt(raw, 10);
    if (isNaN(val) || val < 0) {
      this.cancelEdit();
      return;
    }

    const vm = this.pageData();
    const invItem = vm?.inventoryItems.find(
      (i) => i.date === date && i.roomTypeName === roomTypeName
    );
    const rt = vm?.roomTypes.find((r) => r.name === roomTypeName);
    const total = invItem?.totalRooms ?? 0;

    // Clamp: available cannot exceed total
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

  /** Cancel blackout editing — resets form and clears edit state. */
  cancelEditBlackout() {
    this.editingBlackout.set(null);
    this.blackoutForm.reset({ roomTypeId: '', startDate: '', endDate: '', blockedRooms: 0, reason: '' });
    this.blackoutSelectedRooms.set(new Set<string>());
  }

  /** Cancel inline editing */
  cancelEdit() {
    this.editingCell.set(null);
    this.savingCell.set(null);
  }

  /** Check if a cell is currently being edited inline */
  isEditing(date: string, roomTypeName: string): boolean {
    const edit = this.editingCell();
    return edit?.date === date && edit?.roomTypeName === roomTypeName;
  }

  /** CSS class for a calendar cell based on occupancy */
  cellClass(roomType: CalendarRoomTypeCell): string {
    if (roomType.totalRooms === 0) return 'cell-na';
    const pct = roomType.occupancyPct;
    if (pct >= 90) return 'cell-danger';
    if (pct >= 60) return 'cell-warning';
    if (pct >= 30) return 'cell-caution';
    return 'cell-good';
  }

  /** Occupancy label for a cell */
  cellLabel(roomType: CalendarRoomTypeCell): string {
    if (roomType.totalRooms === 0) return '—';
    return `${roomType.availableRooms}/${roomType.totalRooms}`;
  }

  /** Tooltip text for a cell */
  cellTooltip(roomType: CalendarRoomTypeCell, date: string): string {
    return `${date} · ${roomType.roomTypeName}: ${roomType.availableRooms}/${roomType.totalRooms} disponibles (${roomType.occupancyPct}% ocupado)`;
  }

  /** Check if a cell is the single active cell (for form pre-fill) */
  isSelected(date: string, roomTypeName: string): boolean {
    const cell = this.activeCell();
    return cell?.date === date && cell?.roomTypeName === roomTypeName;
  }

  /** Quick action: pre-fill the blackout form with the selected cell's data */
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

    // Scroll to the blackout form and focus start date
    setTimeout(() => {
      const el = document.querySelector('.form-card:has(#blk-start)');
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      (document.getElementById('blk-start') as HTMLInputElement)?.focus();
    }, 150);
  }

  /** Show confirmation dialog before marking as unavailable. */
  quickMarkUnavailable() {
    const cell = this.activeCell();
    if (!cell) return;

    const vm = this.pageData();
    const invItem = vm?.inventoryItems.find(
      (i) => i.date === cell.date && i.roomTypeName === cell.roomTypeName
    );
    const avail = invItem?.availableRooms ?? 0;
    const total = invItem?.totalRooms ?? 0;

    this.confirmAction.set({
      title: 'Marcar como no disponible',
      message: `Se establecerán 0 habitaciones disponibles para ${cell.roomTypeName} el ${cell.date} (actualmente ${avail} de ${total} disponibles). ¿Desea continuar?`,
      handler: () => this._executeQuickMarkUnavailable(),
    });
  }

  /** Execute the actual mark-unavailable after confirmation. */
  private _executeQuickMarkUnavailable() {
    const cell = this.activeCell();
    if (!cell) return;
    const vm = this.pageData();
    const invItem = vm?.inventoryItems.find(
      (i) => i.date === cell.date && i.roomTypeName === cell.roomTypeName
    );
    const rt = vm?.roomTypes.find((r) => r.name === cell.roomTypeName);
    const total = invItem?.totalRooms ?? 1;

    // Snapshot previous state for undo
    this.undoState.set({
      date: cell.date,
      roomTypeName: cell.roomTypeName,
      roomTypeId: rt?.id ?? cell.roomTypeName,
      totalRooms: total,
      availableRooms: invItem?.availableRooms ?? 0,
      blockedRooms: invItem?.blockedRooms ?? 0,
    });

    // Quick-save: set available=0, blocked=total
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

  /** Handle Escape key — close whatever is open, highest priority first. */
  private _handleEscape() {
    if (this.confirmAction()) {
      this.confirmCancel();
    } else if (this.editingCell()) {
      this.cancelEdit();
    } else if (this.activeCell()) {
      this.activeCell.set(null);
    } else if (this.multiSelectMode()) {
      this.toggleMultiSelect(false);
    }
  }

  /** Arrow-key navigation across the calendar grid. */
  private _navigateArrow(key: string) {
    const cal = this.displayCalendar();
    const vm = this.pageData();
    if (!cal || !vm || cal.days.length === 0 || vm.roomTypes.length === 0) return;

    const roomTypeNames = vm.roomTypes.map(r => r.name);
    const current = this.activeCell();

    let dayIdx = current ? cal.days.findIndex(d => d.date === current.date) : 0;
    let rtIdx = current ? roomTypeNames.indexOf(current.roomTypeName) : 0;

    // Fall back to 0,0 if the current cell is no longer in the view
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

  /** Edit inventory from the data table — pre-fills the inventory form, loads rooms, and scrolls to it. */
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
    // Load hotel rooms so the form shows room checkboxes
    this.onInventoryRoomTypeChange();
    setTimeout(() => {
      const el = document.getElementById('inventory-form-card');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);
  }

  /** Handle delete inventory request — show confirmation dialog. */
  onDeleteInventoryFromTable(item: { date: string; roomTypeName: string }) {
    this.inventoryDeleteConfirm.set({ date: item.date, roomTypeName: item.roomTypeName });
  }

  /** Confirm and execute inventory soft-delete. */
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

    this.api.deleteInventory(propId, rt.id, payload.date).pipe(
      switchMap(() => this.api.getAvailability(propId, 92)),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
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

  /** Handle edit blackout request — pre-fill the blackout form for editing. */
  onEditBlackout(blackoutId: string) {
    const vm = this.pageData();
    if (!vm) return;
    const item = vm.blackoutItems.find(b => b.blackoutId === blackoutId);
    if (!item) return;
    const startDate = item.rangeLabel.split(' -> ')[0];
    const endDate = item.rangeLabel.split(' -> ')[1];
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
    // Fetch rooms and pre-select
    const propId = this.selectedPropId();
    if (propId && item.roomTypeId) {
      this.api.getHotelRooms(propId, item.roomTypeId).subscribe({
        next: (res) => {
          this.hotelRoomsForType.set(res.items);
          const blockedSet = new Set<string>(item.roomNumbers || []);
          this.blackoutSelectedRooms.set(blockedSet.size > 0 ? blockedSet : new Set());
        },
        error: () => {},
      });
    }
    // Scroll to blackout form
    setTimeout(() => {
      const el = document.querySelector('.form-card:has(#blk-start)');
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);
  }

  /** Handle delete blackout request — show confirmation dialog. */
  onDeleteBlackout(blackoutId: string) {
    this.deleteConfirm.set({ blackoutId });
  }

  /** Confirm and execute blackout deletion. */
  confirmDeleteBlackout() {
    const payload = this.deleteConfirm();
    if (!payload) return;
    this.deleteConfirm.set(null);
    const blackoutId = payload.blackoutId;

    this.saving.set(true);

    this.api
      .deleteBlackout(blackoutId)
      .pipe(
        switchMap(() => this.api.getAvailability(this.selectedPropId(), 92)),
        takeUntilDestroyed(this.destroyRef),
      )
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

  /** Accept the confirmation dialog. */
  confirmAccept() {
    const handler = this.confirmAction()?.handler;
    this.confirmAction.set(null);
    if (handler) handler();
  }

  /** Dismiss the confirmation dialog. */
  confirmCancel() {
    this.confirmAction.set(null);
  }

  /** Active cell info label */
  activeCellLabel(): string {
    const cell = this.activeCell();
    if (!cell) return '';
    return `${cell.date} — ${cell.roomTypeName}`;
  }

  /** Undo the last quick action by restoring the previous inventory values. */
  undoQuickAction() {
    const state = this.undoState();
    if (!state) return;

    this.undoState.set(null);
    this._clearUndoTimer();

    this.inventoryForm.patchValue({
      roomTypeId: state.roomTypeId,
      date: state.date,
      totalRooms: state.totalRooms,
      availableRooms: state.availableRooms,
      blockedRooms: state.blockedRooms,
    });
    this.savingCell.set(`${state.date}|${state.roomTypeName}`);
    this.saveInventory();        this.toast.info('Restaurando inventario anterior…');
  }

  /** Dismiss the undo bar without restoring. */
  dismissUndo() {
    this.undoState.set(null);
    this._clearUndoTimer();
  }

  private _clearUndoTimer() {
    if (this._undoTimer) {
      clearTimeout(this._undoTimer);
      this._undoTimer = null;
    }
  }

  private _clearHighlight() {
    if (this._highlightTimer) {
      clearTimeout(this._highlightTimer);
      this._highlightTimer = null;
    }
    this.highlightedCell.set(null);
  }

  /** Sync form totals from room checkbox selections (only for form-based saves). */
  private _syncInventoryFormFromCheckboxes() {
    const totals = this.computedInventoryTotals();
    this.inventoryForm.patchValue({
      totalRooms: totals.total,
      availableRooms: totals.available,
      blockedRooms: totals.blocked,
    });
  }

  saveInventory(): void {
    const propId = this.selectedPropId();
    if (!propId) {
      this.savingCell.set(null);
      return;
    }

    // Validate form values as-is (already set by _autoSaveToggle, commitEdit, or room checkboxes)
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
      .pipe(
        switchMap(() => this.api.getAvailability(propId, 92)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (data) => {
          this.pageData.set(data);
          this.toast.success('Inventario actualizado');
          this._rebuildCalendar();
          this.inventoryForm.reset({
            roomTypeId: '',
            date: '',
            totalRooms: 0,
            availableRooms: 0,
            blockedRooms: 0,
          });
          this.activeCell.set(null);
          this.editingCell.set(null);
          // Clean up room selections for a fresh start on next create
          this.hotelRoomsForType.set([]);
          this.selectedAvailableRooms.set(new Set());
          this.selectedBlockedRooms.set(new Set());

          // Brief green flash + tooltip on the cell that was just saved
          const savedKey = this.savingCell();
          this.savingCell.set(null);
          if (savedKey) {
            this._clearHighlight();
            const [date, rtName] = savedKey.split('|');
            const inv = data.inventoryItems.find(
              (i) => i.date === date && i.roomTypeName === rtName
            );
            const label = inv
              ? `${inv.availableRooms}/${inv.totalRooms} disponibles`
              : 'Actualizado';
            this.highlightedCell.set({ key: savedKey, label });
            this._highlightTimer = setTimeout(() => {
              this.highlightedCell.set(null);
            }, 1200);
          }

          this.saving.set(false);

          // If there's a pending undo state, auto-dismiss after 10 seconds
          if (this.undoState()) {
            this._clearUndoTimer();
            this._undoTimer = setTimeout(() => {
              this.undoState.set(null);
            }, 10000);
          }
        },         error: (err: ApiError) => {
          this.toast.error(err.message || 'Error al guardar inventario.');
          this.savingCell.set(null);
          this._clearHighlight();
          this.saving.set(false);
          // Clear undo state so stale data can't be restored
          this.undoState.set(null);
          this._clearUndoTimer();
        },
      });
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

    if (roomNumbers.length > 0) {
      payload['room_numbers'] = roomNumbers;
    } else {
      payload['blocked_rooms'] = this.blackoutForm.controls.blockedRooms.value;
    }

    const request$ = editing
      ? this.api.updateBlackout(editing.blackoutId, payload)
      : this.api.createBlackout(payload as any);

    request$
      .pipe(
        switchMap(() => this.api.getAvailability(propId, 92)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (data) => {
          this.pageData.set(data);
          this.toast.success('Bloqueo registrado');
          this._rebuildCalendar();
          this.blackoutForm.reset({
            roomTypeId: '',
            startDate: '',
            endDate: '',
            blockedRooms: 0,
            reason: '',
          });
          this.editingBlackout.set(null);
          this.blackoutSelectedRooms.set(new Set());
          this.hotelRoomsForType.set([]);
          this.saving.set(false);
        },          error: (err: ApiError) => {
          this.toast.error(err.message || 'Error al registrar bloqueo.');
          this.saving.set(false);
        },
      });
  }

  private _rebuildCalendar() {
    const vm = this.pageData();
    if (!vm) return;
    if (this.viewMode() === 'month') {
      this.calendarMonth.set(
        buildCalendarMonth(this.calendarYear(), this.calendarMonthIdx(), vm.inventoryItems),
      );
    } else {
      this.calendarWeek.set(
        buildCalendarWeek(this.weekAnchor(), vm.inventoryItems),
      );
    }
  }
}
