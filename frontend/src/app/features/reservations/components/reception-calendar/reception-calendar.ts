import { ChangeDetectionStrategy, Component, computed, effect, inject, input, output, signal } from '@angular/core';

import { DecimalPipe, NgStyle } from '@angular/common';
import { RouterLink } from '@angular/router';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import type { ReceptionCalendarData, ReceptionCalendarDay, ReceptionCalendarReservation } from '../../models/reception-calendar.model';
import { ReservationsApiService } from '../../services/reservations-api.service';

const DAY_NAMES = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];

@Component({
  selector: 'app-reception-calendar',
  imports: [DecimalPipe, EmptyStateComponent, NgStyle, RouterLink],
  templateUrl: './reception-calendar.html',
  styleUrl: './reception-calendar.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReceptionCalendarComponent {
  private readonly api = inject(ReservationsApiService);

  /** Property ID to fetch reservations for. */
  readonly propId = input<number>(0);

  /** Emitted when a reservation bar is clicked. */
  readonly reservationClick = output<ReceptionCalendarReservation>();

  readonly loading = signal(true);
  readonly error = signal(false);
  readonly calendarData = signal<ReceptionCalendarData | null>(null);

  /** Currently visible date range for navigation. */
  readonly viewStartDate = signal('');
  readonly viewEndDate = signal('');

  /** Detail modal state. */
  readonly selectedReservation = signal<ReceptionCalendarReservation | null>(null);
  readonly detailLoading = signal(false);
  readonly detailData = signal<any>(null);

  /** Drag-and-drop state. */
  readonly dragBookingId = signal<string | null>(null);
  readonly dragOverRoom = signal<string | null>(null);
  readonly reassigning = signal(false);
  readonly reassignSuccess = signal<string | null>(null);
  readonly reassignError = signal<string | null>(null);
  readonly reassignConflict = signal<ReceptionCalendarReservation | null>(null);

  readonly today = signal(new Date().toISOString().slice(0, 10));

  /** Computed: days to display in the calendar header. */
  readonly calendarDays = computed<ReceptionCalendarDay[]>(() => {
    const data = this.calendarData();
    if (!data) return [];
    const start = new Date(data.startDate + 'T12:00:00');
    const end = new Date(data.endDate + 'T12:00:00');
    const days: ReceptionCalendarDay[] = [];
    const current = new Date(start);
    while (current <= end) {
      const dateStr = current.toISOString().slice(0, 10);
      days.push({
        date: dateStr,
        day: current.getDate(),
        dayName: DAY_NAMES[current.getDay()],
        isToday: dateStr === this.today(),
        isWeekend: current.getDay() === 0 || current.getDay() === 6,
      });
      current.setDate(current.getDate() + 1);
    }
    return days;
  });

  /** Map of date → column index (0-based). */
  readonly dayIndexMap = computed(() => {
    const map = new Map<string, number>();
    this.calendarDays().forEach((d, i) => map.set(d.date, i));
    return map;
  });

  readonly totalDays = computed(() => this.calendarDays().length);

  /** CSS grid-template-columns value for grid rows. */
  readonly gridCols = computed(() => {
    const n = this.totalDays();
    if (n === 0) return '';
    return `150px repeat(${n}, minmax(32px, 1fr))`;
  });

  constructor() {
    effect(() => {
      const propId = this.propId();
      if (propId > 0) {
        this._loadCalendar();
      } else {
        this.calendarData.set(null);
        this.loading.set(false);
      }
    }, { allowSignalWrites: true });
  }

  /** Public method for retry button. */
  loadCalendar() {
    this._loadCalendar();
  }

  private _loadCalendar() {
    const propId = this.propId();
    if (!propId) { this.loading.set(false); return; }

    this.loading.set(true);
    this.error.set(false);

    this.api.getReceptionCalendar(propId).subscribe({
      next: (data) => {
        this.calendarData.set(data);
        this.today.set(data.today);
        this.viewStartDate.set(data.startDate);
        this.viewEndDate.set(data.endDate);
        this.loading.set(false);
      },
      error: () => { this.error.set(true); this.loading.set(false); },
    });
  }

  navigateWeeks(days: number) {
    const propId = this.propId();
    if (!propId) return;

    const start = new Date(this.viewStartDate() + 'T12:00:00');
    start.setDate(start.getDate() + days);
    const end = new Date(start);
    end.setDate(end.getDate() + 27);

    this.loading.set(true);
    this.api.getReceptionCalendar(propId, start.toISOString().slice(0, 10), end.toISOString().slice(0, 10)).subscribe({
      next: (data) => {
        this.calendarData.set(data);
        this.viewStartDate.set(data.startDate);
        this.viewEndDate.set(data.endDate);
        this.loading.set(false);
      },
      error: () => { this.error.set(true); this.loading.set(false); },
    });
  }

  goToday() {
    const propId = this.propId();
    if (!propId) return;

    const today = new Date();
    const start = new Date(today);
    start.setDate(start.getDate() - 14);
    const end = new Date(today);
    end.setDate(end.getDate() + 14);

    this.loading.set(true);
    this.api.getReceptionCalendar(propId, start.toISOString().slice(0, 10), end.toISOString().slice(0, 10)).subscribe({
      next: (data) => {
        this.calendarData.set(data);
        this.viewStartDate.set(data.startDate);
        this.viewEndDate.set(data.endDate);
        this.loading.set(false);
      },
      error: () => { this.error.set(true); this.loading.set(false); },
    });
  }

  /**
   * Compute the CSS grid-column style for a reservation bar.
   * Returns `{ gridColumn: 'start / end' }` for use with [ngStyle].
   */
  barGridStyle(reservation: ReceptionCalendarReservation): Record<string, string> {
    const dayMap = this.dayIndexMap();
    const total = this.totalDays();
    if (total === 0) return {};

    const ciIdx = dayMap.get(reservation.checkInDate);
    const coIdx = dayMap.get(reservation.checkOutDate);
    if (ciIdx === undefined) return {};

    // Grid is 1-based: col 1 = room label, col 2 = first day, etc.
    const startCol = ciIdx + 2;
    const endCol = (coIdx !== undefined ? coIdx : ciIdx) + 3; // exclusive end

    // Partial-day visual insets via margin (preserves text readability)
    const ciFrac = reservation.checkInFraction;
    const coFrac = reservation.checkOutFraction;
    const hasPartialIn = ciFrac > 0.15;
    const hasPartialOut = coFrac > 0 && coFrac < 0.85 && coIdx !== ciIdx;

    return {
      gridColumn: `${startCol} / ${endCol}`,
      ...(hasPartialIn ? { marginLeft: `${ciFrac * 100}%` } : {}),
      ...(hasPartialOut ? { marginRight: `${(1 - coFrac) * 100}%` } : {}),
    };
  }

  /** CSS class for reservation bar colour. */
  barColorClass(visualStatus: string): string {
    switch (visualStatus) {
      case 'active': return 'bar-active';
      case 'upcoming': return 'bar-upcoming';
      case 'past': return 'bar-past';
      case 'cancelled': return 'bar-cancelled';
      default: return 'bar-upcoming';
    }
  }

  statusLabel(visualStatus: string): string {
    switch (visualStatus) {
      case 'active': return 'Vigente';
      case 'upcoming': return 'Próxima';
      case 'past': return 'Finalizada';
      case 'cancelled': return 'Cancelada';
      default: return visualStatus;
    }
  }

  barTooltip(r: ReceptionCalendarReservation): string {
    const guestLabel = r.children > 0
      ? `${r.adults} adulto(s) + ${r.children} niño(s)`
      : `${r.adults} huésped(es)`;
    return `${r.guestName} · ${guestLabel} · ${r.totalNights} noche(s) · ${r.checkInDate} → ${r.checkOutDate}`;
  }

  openDetail(reservation: ReceptionCalendarReservation, event: Event) {
    event.stopPropagation();
    this.selectedReservation.set(reservation);
    this.reservationClick.emit(reservation);

    this.detailLoading.set(true);
    this.detailData.set(null);
    this.api.getReservationDetail(reservation.bookingId).subscribe({
      next: (data) => { this.detailData.set(data); this.detailLoading.set(false); },
      error: () => this.detailLoading.set(false),
    });
  }

  closeDetail() {
    this.selectedReservation.set(null);
    this.detailData.set(null);
  }

  formatTime(time: string): string {
    return time || '--:--';
  }

  /** Total reservations across all room types. */
  readonly totalReservations = computed(() => {
    const data = this.calendarData();
    if (!data) return 0;
    return data.roomTypes.reduce((sum, rt) => sum + rt.reservations.length, 0);
  });

  // ─── Drag-and-Drop handlers ───

  onDragStart(r: ReceptionCalendarReservation, event: DragEvent) {
    if (!this.canDrag(r)) {
      event.preventDefault();
      return;
    }
    this.dragBookingId.set(r.bookingId);
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', r.bookingId);
    }
  }

  onDragEnd() {
    this.dragBookingId.set(null);
    this.dragOverRoom.set(null);
  }

  onRowDragOver(r: ReceptionCalendarReservation, event: DragEvent) {
    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'move';
    }
    this.dragOverRoom.set(r.roomNumber);
  }

  onRowDragLeave(r: ReceptionCalendarReservation) {
    if (this.dragOverRoom() === r.roomNumber) {
      this.dragOverRoom.set(null);
    }
  }

  onRowDrop(targetReservation: ReceptionCalendarReservation, event: DragEvent) {
    event.preventDefault();
    this.dragOverRoom.set(null);

    const sourceBookingId = this.dragBookingId();
    if (!sourceBookingId) return;

    // Find source reservation from calendar data
    const source = this._findReservation(sourceBookingId);
    if (!source) { this.dragBookingId.set(null); return; }

    // Don't drop on same room
    if (source.hotelRoomId && source.hotelRoomId === targetReservation.hotelRoomId) {
      this.dragBookingId.set(null);
      return;
    }

    const targetRoomId = targetReservation.hotelRoomId;
    if (!targetRoomId || !source.hotelRoomId) {
      this.dragBookingId.set(null);
      return;
    }

    // Conflict detection: warn if target row has an active reservation
    if (targetReservation.visualStatus === 'active' || targetReservation.visualStatus === 'upcoming') {
      this.reassignConflict.set(targetReservation);
      return;
    }

    this._executeReassign(source, targetRoomId, targetReservation.roomNumber);
  }

  confirmReassign() {
    const conflict = this.reassignConflict();
    if (!conflict) return;
    this.reassignConflict.set(null);

    const sourceBookingId = this.dragBookingId();
    if (!sourceBookingId) return;
    const source = this._findReservation(sourceBookingId);
    if (!source) { this.dragBookingId.set(null); return; }

    this._executeReassign(source, conflict.hotelRoomId, conflict.roomNumber);
  }

  cancelReassign() {
    this.reassignConflict.set(null);
    this.dragBookingId.set(null);
  }

  private _executeReassign(
    source: ReceptionCalendarReservation,
    targetRoomId: string,
    targetRoomNumber: string,
  ) {
    this.reassigning.set(true);
    this.reassignSuccess.set(null);
    this.reassignError.set(null);

    this.api.assignRooms(source.bookingId, [targetRoomId]).subscribe({
      next: () => {
        this.reassignSuccess.set(`${source.guestName} → Habitación ${targetRoomNumber}`);
        this.reassigning.set(false);
        this.dragBookingId.set(null);
        this._loadCalendar();
        setTimeout(() => this.reassignSuccess.set(null), 4000);
      },
      error: (err) => {
        this.reassignError.set(err?.error?.detail || 'Error al reasignar habitación');
        this.reassigning.set(false);
        this.dragBookingId.set(null);
        setTimeout(() => this.reassignError.set(null), 5000);
      },
    });
  }

  private _findReservation(bookingId: string): ReceptionCalendarReservation | null {
    const data = this.calendarData();
    if (!data) return null;
    for (const rt of data.roomTypes) {
      for (const r of rt.reservations) {
        if (r.bookingId === bookingId) return r;
      }
    }
    return null;
  }

  isDragOver(roomNumber: string): boolean {
    return this.dragOverRoom() === roomNumber && this.dragBookingId() !== null;
  }

  isDragging(r: ReceptionCalendarReservation): boolean {
    return this.dragBookingId() === r.bookingId;
  }

  canDrag(r: ReceptionCalendarReservation): boolean {
    return (r.visualStatus === 'upcoming' || r.visualStatus === 'active') && !!r.hotelRoomId;
  }
}
