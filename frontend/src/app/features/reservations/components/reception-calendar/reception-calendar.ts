import { ChangeDetectionStrategy, Component, computed, effect, ElementRef, inject, input, output, signal, ViewChild } from '@angular/core';
import { DecimalPipe, NgStyle } from '@angular/common';
import { RouterLink } from '@angular/router';
import { httpResource } from '@angular/common/http';
import { CdkDrag, CdkDropList, CdkDropListGroup, type CdkDragDrop } from '@angular/cdk/drag-drop';
import { CdkTrapFocus } from '@angular/cdk/a11y';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import type {
  ReceptionCalendarData,
  ReceptionCalendarDay,
  ReceptionCalendarReservation,
  ReceptionCalendarRoom,
} from '../../models/reception-calendar.model';
import { ReservationsApiService } from '../../services/reservations-api.service';
import { mapReceptionCalendar, type ReceptionCalendarDto } from '../../services/reservations-api.service';

/**
 * Snake-case wire shape for `/api/reservations/{id}`. Field list mirrors the
 * fields the calendar-popup modal displays; extend when adding new rendered
 * properties. The mapper below is the only place that converts wire → view.
 */
interface ReservationDetailDto {
  booking_id: string;
  prop_id: number | null;
  guest_name: string;
  guest_email?: string | null;
  guest_phone?: string | null;
  status: string;
  check_in: string;
  check_out: string;
  adults: number;
  children: number;
  total_nights: number;
  hotel_room_id?: string | null;
  hotel_room_number?: string | null;
  total_amount: number;
  currency: string;
  source: string;
  source_id?: string | null;
  notes: string;
  created_at: string;
  hotel?: { hotel_label: string } | null;
}

/**
 * CamelCase view-model type emitted by `parse: mapReservationDetail(dto)` on
 * `detailResource` (consumed through the typed signal below).
 */
interface ReservationDetail {
  bookingId: string;
  propId: number | null;
  guestName: string;
  guestEmail: string | null;
  guestPhone: string | null;
  status: string;
  checkIn: string;
  checkOut: string;
  adults: number;
  children: number;
  totalNights: number;
  hotelRoomId: string | null;
  hotelRoomNumber: string | null;
  totalAmount: number;
  currency: string;
  source: string;
  sourceId: string | null;
  notes: string;
  createdAt: string;
  hotel: { hotelLabel: string } | null;
}

/**
 * Inline snake→camel mapper for the reservation-detail endpoint. Lives next to
 * its sole consumer because no other view-model in the codebase currently
 * reads this response; promote to a shared mapper if more callers appear.
 */
function mapReservationDetail(dto: ReservationDetailDto): ReservationDetail {
  return {
    bookingId: dto.booking_id,
    propId: dto.prop_id,
    guestName: dto.guest_name,
    guestEmail: dto.guest_email ?? null,
    guestPhone: dto.guest_phone ?? null,
    status: dto.status,
    checkIn: dto.check_in,
    checkOut: dto.check_out,
    adults: dto.adults,
    children: dto.children,
    totalNights: dto.total_nights,
    hotelRoomId: dto.hotel_room_id ?? null,
    hotelRoomNumber: dto.hotel_room_number ?? null,
    totalAmount: dto.total_amount,
    currency: dto.currency,
    source: dto.source,
    sourceId: dto.source_id ?? null,
    notes: dto.notes,
    createdAt: dto.created_at,
    hotel: dto.hotel ? { hotelLabel: dto.hotel.hotel_label } : null,
  };
}

/** Reservation awaiting user confirmation in the conflict modal. */
type PendingReassign = { source: ReceptionCalendarReservation; targetRoom: ReceptionCalendarRoom };

const DAY_NAMES = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];

@Component({
  selector: 'app-reception-calendar',
  imports: [
    CdkDrag,
    CdkDropList,
    CdkDropListGroup,
    CdkTrapFocus,
    DecimalPipe,
    EmptyStateComponent,
    NgStyle,
    RouterLink,
  ],
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

  /** Currently visible date range for navigation (14-day view). */
  readonly viewStartDate = signal('');
  readonly viewEndDate = signal('');

  readonly today = computed(() => this.calendarResource.value()?.today ?? new Date().toISOString().slice(0, 10));

  constructor() {
    this._resetToThisWeek();

    // Live now-line ticker: refreshes the dot position every 30 s.
    effect((onCleanup) => {
      const intervalId = setInterval(() => this._now.set(new Date()), 30_000);
      onCleanup(() => clearInterval(intervalId));
    });

    // Sync detailResource to detailData/detailLoading signals
    effect(() => {
      const data = this.detailResource.value();
      const loading = this.detailResource.isLoading();
      this.detailData.set(data ?? null);
      this.detailLoading.set(loading);
    });

    // Auto-focus the modal close button on open. cdkTrapFocus only redirects
    // focus WHEN focus tries to leave the trap; on open, focus would otherwise
    // stay on the calendar bar that triggered the modal (hidden under the
    // backdrop from the user's perspective). Predictable programmatic focus
    // via queueMicrotask defers past Angular's view lifecycle.
    effect(() => {
      if (this.selectedReservation() || this.reassignConflict()) {
        queueMicrotask(() => this.modalCloseBtn?.nativeElement?.focus());
      }
    });
  }

  /** Get the Monday of the current week. */
  private _weekStart(date: Date): Date {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Monday
    d.setDate(diff);
    d.setHours(12, 0, 0, 0);
    return d;
  }

  private _toIsoDate(date: Date): string {
    return date.toISOString().slice(0, 10);
  }

  private _resetToThisWeek() {
    const start = this._weekStart(new Date());
    const end = new Date(start);
    end.setDate(end.getDate() + 13);
    this.viewStartDate.set(this._toIsoDate(start));
    this.viewEndDate.set(this._toIsoDate(end));
  }

  // ─── httpResource for calendar data (DTO → ViewModel via parse) ───
  readonly calendarResource = httpResource<ReceptionCalendarData>(() => {
    const propId = this.propId();
    const start = this.viewStartDate();
    const end = this.viewEndDate();
    if (!propId || !start || !end) return undefined;
    const params = new URLSearchParams();
    params.set('prop_id', String(propId));
    params.set('start_date', start);
    params.set('end_date', end);
    const query = params.toString();
    return query ? `/management/reception/calendar?${query}` : '/management/reception/calendar';
  }, {
    parse: (dto) => mapReceptionCalendar(dto as ReceptionCalendarDto),
  });

  /** Live "now" line tracker ────────────────────────────────────────
   *  Re-renders the now-line every 30 s without forcing a grid refresh.
   *  Cheap (a single signal update) and battery-friendly. */
  private readonly _now = signal(new Date());

  /** Index of today's column in the visible range, or -1 when out of view. */
  readonly todayIndex = computed(() => this.dayIndexMap().get(this.today()) ?? -1);

  /** True when today is on-screen — gates rendering the now-line. */
  readonly showNowLine = computed(() => this.totalDays() > 0 && this.todayIndex() >= 0);

  /** Fraction of today's day elapsed: 0 = 00:00, 1 = 24:00. */
  readonly nowFraction = computed(() => {
    const n = this._now();
    return (n.getHours() * 3600 + n.getMinutes() * 60 + n.getSeconds()) / 86_400;
  });

  /** Localised HH:MM label for the dot. */
  readonly nowLineTimeLabel = computed(() => {
    const n = this._now();
    return `${String(n.getHours()).padStart(2, '0')}:${String(n.getMinutes()).padStart(2, '0')}`;
  });

  /** Detail modal state. */
  readonly selectedReservation = signal<ReceptionCalendarReservation | null>(null);
  readonly detailLoading = signal(false);
  readonly detailData = signal<ReservationDetail | null>(null);

  /** httpResource for reservation detail (on-demand via selectedBookingId trigger). */
  readonly selectedBookingId = signal('');
  readonly detailResource = httpResource<ReservationDetail>(() => {
    const id = this.selectedBookingId();
    return id ? `/api/reservations/${id}` : undefined;
  }, {
    parse: (dto) => mapReservationDetail(dto as ReservationDetailDto),
  });

  // ─── Reassignment state (CDK drag-drop) ───
  readonly reassigning = signal(false);
  readonly reassignSuccess = signal<string | null>(null);
  readonly reassignError = signal<string | null>(null);
  /** Blocking reservation at the drop target (room already has active/upcoming booking). */
  readonly reassignConflict = signal<ReceptionCalendarReservation | null>(null);
  /** Held while user resolves the conflict modal. Cleared on confirm/cancel. */
  readonly pendingReassign = signal<PendingReassign | null>(null);

  /** Computed: days to display in the calendar header. */
  readonly calendarDays = computed<ReceptionCalendarDay[]>(() => {
    const data = this.calendarResource.value();
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

  /** Each day column is a fixed 110px wide. The fixed width makes the
   *  pixel offset for the now-line overlay calculable in pure TS without
   *  DOM measurement (see `nowLineLeftPx`), and produces a stable horizontal
   *  scroll bound (140 + 14×110 = 1680px minimum) so the grid behaves
   *  identically across viewports. */
  static readonly DAY_COL_WIDTH_PX = 110;
  static readonly LABEL_COL_WIDTH_PX = 140;

  /** CSS grid-template-columns value for the calendar header and every row. */
  readonly gridCols = computed(() => {
    const n = this.totalDays();
    if (n === 0) return '';
    return `${ReceptionCalendarComponent.LABEL_COL_WIDTH_PX}px repeat(${n}, ${ReceptionCalendarComponent.DAY_COL_WIDTH_PX}px)`;
  });

  /** Captures the modal close button for programmatic focus on modal open.
   *  Same ref name on both modals because they're gated behind mutually exclusive
   *  `@if` blocks — only one renders at a time, so `@ViewChild` resolves to the
   *  currently-mounted instance. */
  @ViewChild('modalCloseBtn', { static: false })
  readonly modalCloseBtn?: ElementRef<HTMLButtonElement>;

  /** Public method for retry button. */
  loadCalendar() {
    this.calendarResource.reload();
  }

  navigateWeek(direction: -1 | 1) {
    const propId = this.propId();
    if (!propId) return;

    const start = new Date(this.viewStartDate() + 'T12:00:00');
    // Navigate in 7-day steps but always show a 14-day window
    start.setDate(start.getDate() + direction * 7);
    const end = new Date(start);
    end.setDate(end.getDate() + 13);

    this.viewStartDate.set(this._toIsoDate(start));
    this.viewEndDate.set(this._toIsoDate(end));
  }

  goThisWeek() {
    this._resetToThisWeek();
  }

  /**
   * Compute the CSS grid-column style for a reservation bar.
   * Returns `{ gridColumn: 'start / end' }` for use with [ngStyle].
   *
   * If check-out falls outside the visible range, the bar extends
   * to the last visible day so reservations aren't clipped at
   * the week boundary.
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
    // If checkout is outside the visible range, extend to the last day + 1
    const lastVisibleIdx = total - 1;
    const endCol = (coIdx !== undefined ? coIdx : lastVisibleIdx) + 3; // exclusive end

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
    this.selectedBookingId.set(reservation.bookingId);
  }

  closeDetail() {
    this.selectedReservation.set(null);
    this.detailData.set(null);
    this.selectedBookingId.set('');
  }

  formatTime(time: string): string {
    return time || '--:--';
  }

  /** Total reservations across all rooms. */
  readonly totalReservations = computed(() => {
    const data = this.calendarResource.value();
    if (!data) return 0;
    return data.rooms.reduce((sum, rm) => sum + rm.reservations.length, 0);
  });

  // ─── Drag-and-drop (Angular CDK) ───

  /** Only upcoming/active reservations with a known room are draggable.
   *  Past/cancelled bars stay put — historical record.
   */
  canDrag(r: ReceptionCalendarReservation): boolean {
    return (r.visualStatus === 'upcoming' || r.visualStatus === 'active') && !!r.hotelRoomId;
  }

  /**
   * Single drop handler. Replaces the previous HTML5 dragstart/dragover/drop
   * state machine that was tracking the dragged booking via `dragBookingId`
   * and re-resolving it through `_findReservation(bookingId)` on each event.
   *
   * CDK (`cdkDropListGroup` on `.rc-grid`) auto-connects every room's
   * `cdkDropList`, so any room can accept any bar. Source/target rooms and
   * the dragged reservation arrive on the event as typed objects, no lookup.
   *
   * If the target room has its own active/upcoming reservation we surface the
   * existing conflict modal. We deliberately do NOT move the bar in CDK's
   * data — after the API call reassigns the booking server-side, the next
   * `calendarResource.reload()` fetches the new location and the bar renders
   * there naturally.
   */
  onBarDropped(
    event: CdkDragDrop<ReceptionCalendarRoom, ReceptionCalendarRoom, ReceptionCalendarReservation>,
  ) {
    if (event.previousContainer === event.container) return;

    const targetRoom = event.container.data;
    const reservation = event.item.data;
    if (!targetRoom || !reservation) return;
    if (!this.canDrag(reservation)) return;

    const blockingReservation = targetRoom.reservations.find(
      r => (r.visualStatus === 'active' || r.visualStatus === 'upcoming')
       && r.bookingId !== reservation.bookingId,
    );

    if (blockingReservation) {
      this.pendingReassign.set({ source: reservation, targetRoom });
      this.reassignConflict.set(blockingReservation);
      return;
    }

    this._executeReassign(reservation, targetRoom.hotelRoomId, targetRoom.roomNumber);
  }

  confirmReassign() {
    const pending = this.pendingReassign();
    if (!pending) return;
    this.reassignConflict.set(null);
    this.pendingReassign.set(null);
    this._executeReassign(pending.source, pending.targetRoom.hotelRoomId, pending.targetRoom.roomNumber);
  }

  cancelReassign() {
    this.reassignConflict.set(null);
    this.pendingReassign.set(null);
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
        this.calendarResource.reload();
        setTimeout(() => this.reassignSuccess.set(null), 4000);
      },
      error: (err) => {
        this.reassignError.set(err?.error?.detail || 'Error al reasignar habitación');
        this.reassigning.set(false);
        setTimeout(() => this.reassignError.set(null), 5000);
      },
    });
  }
}
