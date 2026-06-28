import { computed, Signal, signal } from '@angular/core';

import type { AvailabilityViewModel, HotelRoomInfo } from '../models/availability.model';
import type { CalendarMonth } from '../models/availability.model';

export interface UndoInfo {
  date: string;
  roomTypeName: string;
  roomTypeId: string;
  totalRooms: number;
  availableRooms: number;
  blockedRooms: number;
}

export interface ConfirmConfig {
  title: string;
  message: string;
  handler: () => void;
}

export interface CellEdit {
  date: string;
  roomTypeName: string;
}

export interface BlackoutEdit {
  blackoutId: string;
  roomTypeId: string;
  startDate: string;
  endDate: string;
  reason: string;
  roomNumbers: string[];
}

export type ViewMode = 'month' | 'week';
export type LayoutMode = 'scroll' | 'wrap';

export interface HotelRoomItem {
  hotel_room_id: string;
  room_number: string;
  room_label: string;
  floor: string;
  is_active: boolean;
}

const _roomNumbersByType = (rooms: HotelRoomInfo[]) => {
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
      return !isNaN(na) && !isNaN(nb) ? na - nb : a.localeCompare(b);
    });
  }
  return map;
};

export class AvailabilityState {
  readonly selectedPropId: Signal<number>;
  readonly routePropId: Signal<number>;

  constructor(routePropId: Signal<number>) {
    this.routePropId = routePropId;
    this.selectedPropId = computed(() => routePropId());
  }

  // Data
  readonly viewState = signal<'loading' | 'success' | 'error' | 'empty'>('loading');
  readonly pageData = signal<AvailabilityViewModel | null>(null);
  readonly errorMessage = signal('');
  readonly submitMessage = signal('');
  readonly selectedLabel = computed(() => this.pageData()?.hotelName ?? '');

  // Saving
  readonly saving = signal(false);
  readonly savingCell = signal<string | null>(null);

  // Calendar
  readonly viewMode = signal<ViewMode>('week');
  readonly layoutMode = signal<'scroll' | 'wrap'>('wrap');
  readonly calendarMonth = signal<CalendarMonth | null>(null);
  readonly calendarWeek = signal<CalendarMonth | null>(null);
  readonly calendarYear = signal(new Date().getFullYear());
  readonly calendarMonthIdx = signal(new Date().getMonth());
  readonly weekAnchor = signal<Date>(new Date());
  readonly today = new Date();

  // Cell
  readonly activeCell = signal<CellEdit | null>(null);
  readonly editingCell = signal<CellEdit | null>(null);
  readonly highlightedCell = signal<{ key: string; label: string } | null>(null);

  // Selection
  readonly multiSelectMode = signal(false);
  readonly selectedCells = signal<Set<string>>(new Set());
  lastCellKey = '';
  clearLastCellKey() { this.lastCellKey = ''; }
  hasLastCellKey() { return this.lastCellKey !== ''; }

  // Batch
  readonly batchAvailableValue = signal(0);

  // Hotel rooms
  readonly allHotelRooms = signal<HotelRoomInfo[]>([]);
  readonly hotelRoomsForType = signal<HotelRoomItem[]>([]);
  readonly selectedAvailableRooms = signal<Set<string>>(new Set());
  readonly selectedBlockedRooms = signal<Set<string>>(new Set());
  readonly blackoutSelectedRooms = signal<Set<string>>(new Set());

  // Blackout editing
  readonly editingBlackout = signal<BlackoutEdit | null>(null);

  // Undo
  readonly undoState = signal<UndoInfo | null>(null);
  undoTimer: ReturnType<typeof setTimeout> | null = null;

  // Confirmation
  readonly confirmAction = signal<ConfirmConfig | null>(null);
  readonly deleteConfirm = signal<{ blackoutId: string } | null>(null);
  readonly inventoryDeleteConfirm = signal<{ date: string; roomTypeName: string } | null>(null);

  // UI
  readonly refreshing = signal(false);
  readonly skeletonExiting = signal(false);

  // Computed
  readonly roomNumbersByType = computed(() => _roomNumbersByType(this.allHotelRooms()));

  readonly computedInventoryTotals = computed(() => {
    const available = this.selectedAvailableRooms();
    const blocked = this.selectedBlockedRooms();
    return { total: available.size + blocked.size, available: available.size, blocked: blocked.size };
  });
}
