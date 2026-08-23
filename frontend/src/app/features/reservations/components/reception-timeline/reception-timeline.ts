import { AfterViewInit, ChangeDetectionStrategy, Component, computed, ElementRef, HostListener, inject, input, OnDestroy, output, signal, ViewChild } from '@angular/core';
import { Router } from '@angular/router';
import { L10n, loadCldr, setCulture } from '@syncfusion/ej2-base';
// Datos CLDR vendidos localmente (src/cldr/) en lugar del paquete cldr-data,
// cuyo postinstall descarga ~300 MB de GitHub en cada `npm ci` y rompía los
// builds con redes lentas (TLS timeout en cldr-data-downloader). Solo se
// usaban estos 6 JSON (~164 KB) para `loadCldr` + locale es de Syncfusion.
import * as numberingSystems from '../../../../../cldr/supplemental/numberingSystems.json';
import * as likelySubtags from '../../../../../cldr/supplemental/likelySubtags.json';
import * as weekData from '../../../../../cldr/supplemental/weekData.json';
import * as gregorian from '../../../../../cldr/main/es/ca-gregorian.json';
import * as numbers from '../../../../../cldr/main/es/numbers.json';
import * as timeZoneNames from '../../../../../cldr/main/es/timeZoneNames.json';
import { httpResource } from '@angular/common/http';
import {
  ScheduleComponent,
  ScheduleModule,
  TimelineMonthService,
  TimelineViewsService,
} from '@syncfusion/ej2-angular-schedule';
import type {
  ActionEventArgs,
  CellClickEventArgs,
  EventClickArgs,
  NavigatingEventArgs,
  EventRenderedArgs,
  EventSettingsModel,
  PopupOpenEventArgs,
  RenderCellEventArgs,
  ResourcesModel,
  SelectEventArgs,
} from '@syncfusion/ej2-schedule';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ReservationDetailModalComponent } from '../reservation-detail-modal/reservation-detail-modal';
import { ThemeService } from '../../../../core/theme/theme.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { statusColor } from '../../../../shared/utils/semantic-color.helper';
import type {
  ReceptionCalendarData,
  ReceptionCalendarReservation,
} from '../../models/reception-calendar.model';
import { mapReceptionCalendar, type ReceptionCalendarDto } from '../../services/reservations-api.service';
import {
  type PaginatedResponse,
  type RoomStatusItem,
} from '../../../housekeeping/services/housekeeping-api.service';

interface TimelineSelection {
  roomId: string;
  roomNumber: string;
  roomTypeId: string;
  roomTypeName: string;
  startDate: string;
  endDate: string;
  checkInTime: string;
  checkOutTime: string;
}

const ROOM_STATUS_LABELS: Record<string, string> = {
  vacant_dirty: 'Vacante sucia',
  vacant_clean: 'Vacante limpia',
  occupied_clean: 'Ocupada limpia',
  occupied_dirty: 'Ocupada sucia',
  cleaning_in_progress: 'Limpieza en progreso',
  cleaning_completed: 'Limpieza completada',
  inspected: 'Inspeccionada',
  out_of_service: 'Fuera de servicio',
  out_of_order: 'Fuera de orden',
  maintenance_requested: 'Mantenimiento solicitado',
};

function roomStatusColor(status: string): string {
  switch (status) {
    case 'vacant_clean':
    case 'occupied_clean':
    case 'cleaning_completed':
      return statusColor('completed');
    case 'vacant_dirty':
    case 'occupied_dirty':
    case 'cleaning_in_progress':
    case 'maintenance_requested':
      return statusColor(status === 'cleaning_in_progress' ? 'in_progress' : 'dirty');
    case 'inspected':
      return statusColor('inspection');
    case 'out_of_order':
      return statusColor('out_of_order');
    case 'out_of_service':
      return statusColor('inactive');
    default:
      return statusColor(null);
  }
}

type TimelineView = 'TimelineWeek' | 'TimelineMonth';

/** Height shared by the monthly appointment and Syncfusion's overlap lane math. */
const MONTHLY_APPOINTMENT_HEIGHT = '4.5rem';

interface TimelineEvent {
  Id: string;
  Subject: string;
  StartTime: Date;
  EndTime: Date;
  RoomId: string;
  FloorId: string;
  RoomTypeId: string;
  BookingId: string;
  IsAllDay: boolean;
  GuestName: string;
  VisualStatus: ReceptionCalendarReservation['visualStatus'];
  StatusLabel: string;
  RoomNumber: string;
  CheckInDate: string;
  CheckInTime: string;
  EstimatedArrivalTime: string;
  LateCheckin: boolean;
  StayStatus: string;
  /** Ventana de reapertura de no-show: 'open' | 'too_late' | 'stay_ended' | null. */
  ReopenWindow: ReceptionCalendarReservation['reopenWindow'];
  CheckOutDate: string;
  CheckOutTime: string;
  TotalNights: number;
  Adults: number;
  Children: number;
  TotalPrice: number | null;
  Currency: string;
  IsReadonly: boolean;
}

loadCldr(numberingSystems, likelySubtags, weekData, gregorian, numbers, timeZoneNames);
setCulture('es');

L10n.load({
  es: {
    schedule: {
      day: 'Día',
      week: 'Semana',
      workWeek: 'Semana laboral',
      month: 'Mes',
      timelineWeek: 'Semana de timeline',
      timelineMonth: 'Mes de timeline',
      today: 'Hoy',
      noEvents: 'Sin reservas',
      emptyContainer: 'No hay reservas en este periodo',
      previous: 'Periodo anterior',
      next: 'Periodo siguiente',
      start: 'inicio',
      endAt: 'fin',
      allDay: 'Todo el día',
      close: 'Cerrar',
      moreEvents: 'reservas más',
    },
  },
});

@Component({
  selector: 'app-reception-timeline',
  imports: [EmptyStateComponent, ReservationDetailModalComponent, ScheduleModule],
  providers: [TimelineViewsService, TimelineMonthService],
  templateUrl: './reception-timeline.html',
  styleUrl: './reception-timeline.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReceptionTimelineComponent implements AfterViewInit, OnDestroy {
  private readonly router = inject(Router);
  private readonly themeService = inject(ThemeService);
  private readonly toast = inject(ToastService);
  private readonly operationMode = inject(OperationModeService);
  readonly isDark = this.themeService.isDark;

  private readonly dayFormatter = new Intl.DateTimeFormat('es-MX', {
    day: '2-digit',
    month: 'short',
  });

  readonly propId = input.required<number>();
  readonly reservationClick = output<ReceptionCalendarReservation>();

  /** Vista principal del timeline: por defecto mensual (operación a golpe de vista). */
  readonly currentView = signal<TimelineView>('TimelineMonth');
  readonly viewStartDate = signal(this.toIsoDate(this.monthStart(new Date())));
  /** El backend consulta el rango visible de la vista activa. */
  readonly viewEndDate = computed(() => this.addDays(this.viewStartDate(), 6));
  readonly dataStartDate = computed(() => this.currentView() === 'TimelineMonth'
    ? this.toIsoDate(this.monthGridStart(new Date(`${this.viewStartDate()}T12:00:00`)))
    : this.viewStartDate());
  readonly dataEndDate = computed(() => this.currentView() === 'TimelineMonth'
    ? this.toIsoDate(this.monthGridEnd(new Date(`${this.viewStartDate()}T12:00:00`)))
    : this.addDays(this.viewStartDate(), 6));
  readonly selectedDate = computed(() => new Date(`${this.viewStartDate()}T12:00:00`));

  /** Hotel-wide policy defaults (HH:MM) for prefilling a new reservation. */
  readonly policyCheckInTime = computed(() => this.calendarResource.value()?.checkInTime ?? '');
  readonly policyCheckOutTime = computed(() => this.calendarResource.value()?.checkOutTime ?? '');

  readonly housekeepingResource = httpResource<PaginatedResponse<RoomStatusItem>>(() => {
    const propId = this.propId();
    if (!propId) return undefined;
    return `/housekeeping/room-status?prop_id=${propId}&page=1&page_size=200`;
  });

  readonly roomStatuses = computed(() => {
    const resource = this.housekeepingResource;
    // El estado operativo es decorativo: si housekeeping no está disponible
    // (403 por permisos o error de red) el timeline debe seguir funcionando.
    // `resource.value()` LANZA `ResourceValueError` cuando el recurso quedó
    // en estado error (ver _resource-chunk.mjs), y este computed alimenta
    // `resources`, que el Schedule re-lee en CADA render — el throw rompía
    // la cuadrícula al navegar (botones ◀ ▶ y Hoy). Guardar por `error()`
    // evita leer `.value()` en ese estado; la leyenda ya avisa al usuario.
    if (resource.error()) return new Map();
    const statuses = resource.value()?.items ?? [];
    return new Map(statuses.map((item) => [item.hotelRoomId, item]));
  });

  readonly calendarResource = httpResource<ReceptionCalendarData>(() => {
    const propId = this.propId();
    const start = this.dataStartDate();
    const end = this.dataEndDate();
    if (!propId || !start || !end) return undefined;
    return `/management/reception/calendar?prop_id=${propId}&start_date=${start}&end_date=${end}`;
  }, {
    parse: (dto) => mapReceptionCalendar(dto as ReceptionCalendarDto),
  });

  readonly resources = computed<ResourcesModel[]>(() => {
    const data = this.calendarResource.value();
    if (!data) return [];
    const floorResources = new Map<string, {
      Id: string;
      FloorName: string;
      DisplayName: string;
      ResourceKind: 'floor';
      ResourceLevel: 'floor';
      CssClass: string;
    }>();
    const roomTypeResources = new Map<string, {
      Id: string;
      FloorId: string;
      RoomTypeName: string;
      DisplayName: string;
      ResourceKind: 'roomType';
      ResourceLevel: 'roomType';
      CssClass: string;
    }>();
    const floorIdFor = (floor: string): string => this.floorResourceId(floor);
    const roomTypeIdFor = (room: ReceptionCalendarData['rooms'][number]): string =>
      this.roomTypeResourceId(room);

    for (const room of data.rooms) {
      const floor = this.displayValue(room.floor, 'Sin piso');
      const floorId = floorIdFor(floor === 'Sin piso' ? '' : floor);
      const roomTypeId = roomTypeIdFor(room);
      const roomTypeName = this.displayValue(room.roomTypeName, 'Sin tipo');
      if (!floorResources.has(floorId)) {
        floorResources.set(floorId, {
          Id: floorId,
          FloorName: floor === 'Sin piso' ? floor : `Piso ${floor}`,
          DisplayName: floor === 'Sin piso' ? floor : `Piso ${floor}`,
          ResourceKind: 'floor',
          ResourceLevel: 'floor',
          CssClass: 'timeline-resource-group',
        });
      }
      if (!roomTypeResources.has(roomTypeId)) {
        roomTypeResources.set(roomTypeId, {
          Id: roomTypeId,
          FloorId: floorId,
          RoomTypeName: roomTypeName,
          DisplayName: roomTypeName,
          ResourceKind: 'roomType',
          ResourceLevel: 'roomType',
          CssClass: 'timeline-resource-group',
        });
      }
    }

    return [
      {
        field: 'FloorId',
        title: 'Piso',
        name: 'Floors',
        allowMultiple: false,
        textField: 'FloorName',
        idField: 'Id',
        cssClassField: 'CssClass',
        dataSource: [...floorResources.values()],
      },
      {
        field: 'RoomTypeId',
        title: 'Tipo de habitación',
        name: 'RoomTypes',
        groupIDField: 'FloorId',
        allowMultiple: false,
        textField: 'RoomTypeName',
        idField: 'Id',
        cssClassField: 'CssClass',
        dataSource: [...roomTypeResources.values()],
      },
      {
        field: 'RoomId',
        title: 'Habitación',
        name: 'HotelRooms',
        groupIDField: 'RoomTypeId',
        allowMultiple: false,
        textField: 'RoomNumber',
        idField: 'Id',
        colorField: 'Color',
        cssClassField: 'CssClass',
        dataSource: data.rooms.map((room) => ({
          Id: this.displayValue(room.hotelRoomId, 'UNASSIGNED'),
          RoomId: this.displayValue(room.hotelRoomId, 'UNASSIGNED'),
          FloorId: floorIdFor(this.displayValue(room.floor, '')),
          RoomTypeId: roomTypeIdFor(room),
          RoomNumber: this.displayValue(room.roomNumber, 'Sin número'),
          RoomTypeName: this.displayValue(room.roomTypeName, 'Sin tipo'),
          DisplayName: this.displayValue(room.roomNumber, 'Sin número'),
          Floor: this.displayValue(room.floor, ''),
          IsUnassigned: room.hotelRoomId === 'UNASSIGNED',
          RoomTypeValue: this.displayValue(room.roomTypeId, ''),
          ResourceKind: 'room' as const,
          ResourceLevel: 'room' as const,
          Color: this.roomColor(this.displayValue(room.roomTypeId, 'default')),
          CssClass: 'timeline-physical-room',

          OperationalStatus: this.roomStatuses().get(room.hotelRoomId)?.status ?? '',
          OperationalStatusLabel: this.operationalStatusLabel(room.hotelRoomId),
          OperationalStatusColor: this.operationalStatusColor(room.hotelRoomId),
        })),
      },
    ];
  });

  readonly events = computed<TimelineEvent[]>(() => {
    const data = this.calendarResource.value();
    if (!data) return [];

    const reservationEvents: TimelineEvent[] = data.rooms.flatMap((room) => room.reservations.map((reservation) => ({
      Id: reservation.bookingId,
      Subject: this.displayValue(reservation.guestName, 'Reserva sin huésped'),
      StartTime: this.toDate(reservation.checkInDate, reservation.checkInTime),
      EndTime: this.toDate(reservation.checkOutDate, reservation.checkOutTime),
      RoomId: room.hotelRoomId,
      FloorId: this.floorResourceId(room.floor),
      RoomTypeId: this.roomTypeResourceId(room),
      BookingId: reservation.bookingId,
      IsAllDay: false,
      GuestName: this.displayValue(reservation.guestName, 'Reserva sin huésped'),
      VisualStatus: reservation.visualStatus,
      StatusLabel: this.statusLabel(reservation.visualStatus),
      RoomNumber: this.displayValue(reservation.roomNumber || room.roomNumber, 'Sin número'),
      CheckInDate: reservation.checkInDate,
      CheckInTime: reservation.checkInTime,
      EstimatedArrivalTime: reservation.estimatedArrivalTime || '',
      LateCheckin: !!reservation.lateCheckin,
      StayStatus: reservation.stayStatus || '',
      ReopenWindow: reservation.reopenWindow ?? null,
      CheckOutDate: reservation.checkOutDate,
      CheckOutTime: reservation.checkOutTime,
      TotalNights: reservation.totalNights,
      Adults: reservation.adults,
      Children: reservation.children,
      TotalPrice: reservation.totalPrice,
      Currency: this.displayValue(reservation.currency, 'USD'),
      IsReadonly: reservation.visualStatus !== 'active' && reservation.visualStatus !== 'upcoming',
    })));

    return reservationEvents;
  });

  readonly scheduleGroup = { resources: ['Floors', 'RoomTypes', 'HotelRooms'] };


  readonly eventSettings = computed<EventSettingsModel>(() => ({
    dataSource: this.events(),
    enableTooltip: false,
    // Este Timeline no es un editor: evita que Syncfusion abra EventWindow.
    allowAdding: false,
    allowEditing: false,
    allowDeleting: false,
    fields: {
      id: 'Id',
      subject: { name: 'Subject' },
      startTime: { name: 'StartTime' },
      endTime: { name: 'EndTime' },
      isReadonly: 'IsReadonly',
      isAllDay: { name: 'IsAllDay' },
    },
  }));

  @ViewChild('hotelSchedule', { static: false })
  readonly hotelSchedule?: ScheduleComponent;

  @ViewChild('selectionPopover', { static: false })
  readonly selectionPopover?: ElementRef<HTMLDivElement>;

  readonly selectedSlot = signal<TimelineSelection | null>(null);
  readonly selectionPopoverPosition = signal({ top: 0, left: 0 });
  private selectedAnchor: HTMLElement | null = null;
  private selectionPositionFrame: number | null = null;
  private cellSelectionFrame: number | null = null;
  private scrollToCurrentTimeFrame: number | null = null;
  private lastCellSelectionKey = '';
  /** Primer posicionamiento automático de la vista semanal en el día actual. */
  private pendingScrollToToday = false;
  /** Línea vertical "ahora": indicador de la hora local sobre la cuadrícula. */
  private nowLineFrame: number | null = null;
  private nowLineElement: HTMLElement | null = null;
  private nowLineTimer: number | null = null;

  ngAfterViewInit(): void {
    this.disableNativeEditor();
    this.guardSyncfusionPopupDestroy();
    this.startNowLineTimer();
    this.scheduleNowLine();
  }

  ngOnDestroy(): void {
    if (this.selectionPositionFrame !== null) {
      cancelAnimationFrame(this.selectionPositionFrame);
      this.selectionPositionFrame = null;
    }
    if (this.cellSelectionFrame !== null) {
      cancelAnimationFrame(this.cellSelectionFrame);
      this.cellSelectionFrame = null;
    }
    if (this.scrollToCurrentTimeFrame !== null) {
      cancelAnimationFrame(this.scrollToCurrentTimeFrame);
      this.scrollToCurrentTimeFrame = null;
    }
    this.stopNowLineTimer();
    if (this.nowLineFrame !== null) {
      cancelAnimationFrame(this.nowLineFrame);
      this.nowLineFrame = null;
    }
    this.nowLineElement?.remove();
    this.nowLineElement = null;
  }

  @HostListener('window:resize')
  onWindowResize(): void {
    if (this.selectedAnchor && this.selectedSlot()) {
      this.positionSelectionPopover(this.selectedAnchor);
    }
    this.scheduleNowLine();
    // El ancho y la altura de las barras cambian con el viewport: conserva
    // visibles todos los indicadores y deja que el layout apilado se refluya.
    this.hotelSchedule?.element
      .querySelectorAll<HTMLElement>('.e-appointment')
      .forEach((appointment) => this.applyMetaDisclosure(appointment));
  }

  /**
   * Cierra el panel de selección al hacer click en cualquier otra parte del
   * sistema. Los clicks dentro del panel se ignoran (sus botones ya gestionan
   * su propia acción) y los clicks dentro del Scheduler quedan a cargo de
   * `onSelect`: así una nueva selección reemplaza el panel en lugar de
   * cerrarlo por el camino del listener de documento.
   */
  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.selectedSlot()) return;
    const target = event.target;
    if (!(target instanceof Node)) return;

    const popover = this.selectionPopover?.nativeElement;
    if (popover && popover.contains(target)) return;

    const schedule = this.hotelSchedule;
    if (schedule?.element && schedule.element.contains(target)) return;

    this.dismissSelection();
    schedule?.removeSelectedClass();
  }

  readonly selectedEvent = signal<TimelineEvent | null>(null);
  readonly selectedReservation = computed<ReceptionCalendarReservation | null>(() => {
    const event = this.selectedEvent();
    return event ? this.reservationForEvent(event) : null;
  });

  private readonly monthFormatter = new Intl.DateTimeFormat('es-MX', {
    month: 'long',
    year: 'numeric',
  });

  readonly rangeLabel = computed(() => {
    const start = new Date(`${this.viewStartDate()}T12:00:00`);
    if (this.currentView() === 'TimelineMonth') return this.monthFormatter.format(start);
    const end = new Date(`${this.viewEndDate()}T12:00:00`);
    return `${this.dayFormatter.format(start)} — ${this.dayFormatter.format(end)}`;
  });

  readonly totalReservations = computed(() => this.events().length);

  occupancyForDate(value: unknown): number {
    const date = value instanceof Date ? value : new Date(String(value));
    if (Number.isNaN(date.getTime())) return 0;
    const dateIso = this.toIsoDate(date);
    const rooms = (this.calendarResource.value()?.rooms ?? [])
      .filter((room) => room.hotelRoomId !== 'UNASSIGNED');
    if (rooms.length === 0) return 0;

    const occupiedRooms = rooms.filter((room) => room.reservations.some((reservation) =>
      reservation.visualStatus !== 'cancelled'
      && reservation.checkInDate <= dateIso
      && dateIso < reservation.checkOutDate,
    )).length;
    return Math.round((occupiedRooms / rooms.length) * 100);
  }

  formatTimelineDate(value: unknown): string {
    const date = value instanceof Date ? value : new Date(String(value));
    if (Number.isNaN(date.getTime())) return '';
    return new Intl.DateTimeFormat('es-MX', this.currentView() === 'TimelineMonth'
      ? { day: 'numeric' }
      : { weekday: 'short', day: 'numeric', month: 'short' }).format(date);
  }

  dateContext(value: unknown): 'past' | 'outside' | 'current' {
    const date = value instanceof Date ? value : new Date(String(value));
    if (Number.isNaN(date.getTime())) return 'current';

    if (this.currentView() === 'TimelineMonth') {
      const visibleMonth = new Date(`${this.viewStartDate()}T12:00:00`);
      if (
        date.getFullYear() !== visibleMonth.getFullYear()
        || date.getMonth() !== visibleMonth.getMonth()
      ) {
        return 'outside';
      }
    }

    return this.toIsoDate(date) < this.toIsoDate(new Date()) ? 'past' : 'current';
  }

  onRenderCell(args: RenderCellEventArgs): void {
    if (args.elementType !== 'workCells' && args.elementType !== 'monthCells') return;
    if (!args.date) return;

    args.element.classList.add(`timeline-${this.dateContext(args.date)}-day-cell`);
  }

  occupancyTone(value: unknown): string {
    const percentage = this.occupancyForDate(value);
    if (percentage >= 90) return 'high';
    if (percentage >= 60) return 'medium';
    return 'low';
  }

  navigate(direction: -1 | 1): void {
    this.closeDetail();
    const next = this.currentView() === 'TimelineMonth'
      ? this.addMonths(this.viewStartDate(), direction)
      : this.addDays(this.viewStartDate(), direction * 7);
    this.viewStartDate.set(next);
  }

  goToday(): void {
    this.closeDetail();
    const today = new Date();
    const isTimelineWeek = this.currentView() === 'TimelineWeek';
    const targetDate = isTimelineWeek
      ? this.weekStart(today)
      : this.monthStart(today);
    this.viewStartDate.set(this.toIsoDate(targetDate));
    // Syncfusion no reacciona automáticamente a cambios posteriores de
    // [selectedDate] — usar la API pública del componente para forzar la
    // navegación al mes/semana actual en ambas vistas.
    if (this.hotelSchedule) {
      this.hotelSchedule.selectedDate = targetDate;
    }
    // La vista semanal es por horas: "Hoy" navega a la semana actual y además
    // desplaza el scroll horizontal hasta la hora actual del día, para que
    // (p. ej. un domingo) no quede lejos del primer día de la semana.
    if (isTimelineWeek) this.scrollToCurrentTime(today);
  }

  /**
   * Syncfusion dispara `dataBound` tras cada render de la vista. Se usa para
   * posicionar el scroll inicial de la vista semanal en el día/hora actual al
   * abrir la página o al cambiar de Mes → Semana.
   */
  onDataBound(): void {
    // Re-ancla y reposiciona la línea "ahora" tras cada render de la vista
    // (navegación, cambio de vista o carga de datos).
    this.scheduleNowLine();
    // Cubre también estados iniciales con nodos pre-colapsados: la columna de
    // recursos es la fuente de verdad de qué filas están ocultas.
    this.syncCollapsedRows();
    if (this.currentView() !== 'TimelineWeek' || this.pendingScrollToToday) return;
    // En el primer render el @ViewChild puede no estar resuelto todavía; si no
    // hay instancia del schedule se descarta este disparo y el siguiente
    // dataBound (tras la carga de datos) reintentará el posicionamiento.
    if (!this.hotelSchedule) return;
    this.pendingScrollToToday = true;
    this.scrollToCurrentTime(new Date());
  }

  /**
   * Desplaza el scroll horizontal del Timeline hasta ~1 hora antes de la
   * hora actual del día, para que la línea "ahora" no quede pegada al borde
   * inicial del calendario. El objetivo se recorta al inicio de la semana
   * visible (p. ej. lunes 00:30 → domingo 23:30 de la semana anterior no
   * puede posicionarse dentro del rango). Se difiere dos frames para que
   * Syncfusion haya renderizado la semana y la cuadrícula con el nuevo rango
   * antes de calcular la posición X.
   */
  private scrollToCurrentTime(date: Date): void {
    const schedule = this.hotelSchedule;
    if (!schedule) return;
    const target = new Date(date.getTime() - 60 * 60 * 1000);
    const weekStart = new Date(`${this.toIsoDate(this.weekStart(date))}T00:00:00`);
    const clamped = target.getTime() < weekStart.getTime() ? weekStart : target;
    const hour = `${String(clamped.getHours()).padStart(2, '0')}:${String(clamped.getMinutes()).padStart(2, '0')}`;
    if (this.scrollToCurrentTimeFrame !== null) {
      cancelAnimationFrame(this.scrollToCurrentTimeFrame);
    }
    this.scrollToCurrentTimeFrame = requestAnimationFrame(() => {
      this.scrollToCurrentTimeFrame = requestAnimationFrame(() => {
        this.scrollToCurrentTimeFrame = null;
        schedule.scrollTo(hour, clamped);
      });
    });
  }

  /**
   * Programa (en dos frames) el anclado de la línea "ahora". Se difiere para
   * que Syncfusion haya renderizado la cuadrícula y el header antes de medir
   * el ancho de columna y la posición X.
   */
  private scheduleNowLine(): void {
    if (this.nowLineFrame !== null) {
      cancelAnimationFrame(this.nowLineFrame);
    }
    this.nowLineFrame = requestAnimationFrame(() => {
      this.nowLineFrame = requestAnimationFrame(() => {
        this.nowLineFrame = null;
        this.ensureNowLine();
      });
    });
  }

  private startNowLineTimer(): void {
    this.stopNowLineTimer();
    // Se llama a `ensureNowLine` (no a `updateNowLine`) para que la línea
    // se auto-re-ancle si Syncfusion re-crea el `.e-content-wrap` sin
    // disparar `dataBound`; el chequeo de `parentElement` es barato.
    this.nowLineTimer = window.setInterval(() => this.ensureNowLine(), 30_000);
  }

  private stopNowLineTimer(): void {
    if (this.nowLineTimer !== null) {
      window.clearInterval(this.nowLineTimer);
      this.nowLineTimer = null;
    }
  }

  /**
   * Crea (o re-engancha) la línea "ahora" dentro del contenedor scrolleable
   * de la cuadrícula (`.e-content-wrap`). Al vivir dentro del scroll, la
   * línea se mueve con el contenido al desplazarse en horizontal y vertical.
   */
  private ensureNowLine(): void {
    const schedule = this.hotelSchedule;
    if (!schedule) return;
    const wrap = schedule.element.querySelector<HTMLElement>('.e-content-wrap');
    if (!wrap) return;
    if (this.nowLineElement && this.nowLineElement.parentElement === wrap) {
      this.updateNowLine();
      return;
    }
    if (this.nowLineElement) this.nowLineElement.remove();
    this.nowLineElement = document.createElement('div');
    this.nowLineElement.className = 'timeline-now-line';
    this.nowLineElement.setAttribute('role', 'presentation');
    this.nowLineElement.innerHTML = '<span class="timeline-now-line-label"></span>';
    wrap.appendChild(this.nowLineElement);
    this.updateNowLine();
  }

  /**
   * Posiciona la línea en la columna del día actual. Usa como fuente de
   * verdad la API pública de Syncfusion, no heurísticas de DOM ni la señal
   * `currentView()`:
   *
   * - `schedule.getCurrentViewDates()` devuelve `activeView.renderDates`, las
   *   fechas exactas renderizadas de la vista activa (7 en Semana; la
   *   cuadrícula completa de 5–6 semanas en Mes). `dayIndex` se resuelve por
   *   búsqueda directa de hoy en esa lista, con lo que siempre coincide con
   *   la columna pintada, sin matemática manual de inicios de cuadrícula.
   * - `schedule.currentView` (propiedad de la librería) distingue la vista
   *   por horas (TimelineWeek) de la de días (TimelineMonth): en Semana la
   *   línea suma la fracción exacta de la hora (la columna representa 24h) y
   *   en Mes queda al inicio de la columna del día (aproximado a la celda).
   * - El ancho de columna de día se deriva de la propia tabla de contenido
   *   (`offsetWidth / nº de fechas renderizadas`), garantizando que la
   *   posición X corresponda 1:1 con las columnas pintadas.
   * - Si "hoy" no está en el rango visible la línea se oculta.
   */
  private updateNowLine(): void {
    const line = this.nowLineElement;
    const schedule = this.hotelSchedule;
    if (!line || !schedule) return;
    const wrap = schedule.element.querySelector<HTMLElement>('.e-content-wrap');
    if (!wrap || line.parentElement !== wrap) return;

    const contentTable = wrap.querySelector<HTMLElement>('.e-content-table');
    if (!contentTable) {
      line.style.display = 'none';
      return;
    }

    const renderDates = schedule.getCurrentViewDates();
    if (renderDates.length === 0) {
      line.style.display = 'none';
      return;
    }

    const now = new Date();
    const nowIso = this.toIsoDate(now);
    const dayIndex = renderDates.findIndex((date) => this.toIsoDate(date) === nowIso);
    if (dayIndex < 0) {
      line.style.display = 'none';
      return;
    }

    const totalWidth = contentTable.offsetWidth;
    if (totalWidth <= 0) {
      line.style.display = 'none';
      return;
    }
    const isHourView = schedule.currentView === 'TimelineWeek';
    const dayWidth = totalWidth / renderDates.length;
    // La fracción de hora asume columnas de día de 24h (el componente no
    // configura workHours/startHour/endHour, así que la jornada visible es
    // 00:00–24:00). Si algún día se acota la jornada, habrá que derivar la
    // fracción de las horas visibles reales. En Semana la fracción es la hora
    // exacta; en Mes se usa 0.5 para aproximar la línea al CENTRO de la
    // columna del día (sin granularidad horaria, como corresponde a una
    // vista por días).
    const fraction = isHourView
      ? (now.getHours() * 60 + now.getMinutes()) / (24 * 60)
      : 0.5;
    const left = (contentTable.offsetLeft ?? 0) + (dayIndex + fraction) * dayWidth;
    const height = contentTable.offsetHeight;

    line.style.display = 'block';
    line.style.top = '0px';
    line.style.left = `${left}px`;
    line.style.height = `${height}px`;
    line.setAttribute(
      'aria-label',
      `Hora actual: ${now.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })}`,
    );
    const label = line.querySelector<HTMLElement>('.timeline-now-line-label');
    if (label) {
      label.textContent = `Ahora · ${now.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' })}`;
    }
  }

  setView(view: TimelineView): void {
    if (view === this.currentView()) return;
    this.closeDetail();
    // Al volver de Mes → Semana se permite recentrar el scroll en el día
    // actual de nuevo (el dataBound posterior lo hará).
    if (view === 'TimelineWeek') this.pendingScrollToToday = false;
    const currentDate = new Date(`${this.viewStartDate()}T12:00:00`);
    this.currentView.set(view);
    this.viewStartDate.set(this.toIsoDate(
      view === 'TimelineMonth' ? this.monthStart(currentDate) : this.weekStart(currentDate),
    ));
  }

  onNavigating(args: NavigatingEventArgs): void {
    this.closeDetail();
    const nextView: TimelineView = args.currentView === 'TimelineMonth'
      ? 'TimelineMonth'
      : args.currentView === 'TimelineWeek'
        ? 'TimelineWeek'
        : this.currentView();
    const nextDate = args.currentDate ?? this.selectedDate();
    const nextStart = nextView === 'TimelineMonth'
      ? this.monthStart(nextDate)
      : this.weekStart(nextDate);

    this.currentView.set(nextView);
    this.viewStartDate.set(this.toIsoDate(nextStart));
  }

  reload(): void {
    this.calendarResource.reload();
    this.housekeepingResource.reload();
  }

  /**
   * Evita cualquier apertura programática del EventWindow nativo. La selección
   * de celdas sigue funcionando porque no se modifica `select` ni el Schedule
   * en modo readonly; solo se desactiva el editor que este Timeline no usa.
   */
  onScheduleCreated(): void {
    this.disableNativeEditor();
    this.guardSyncfusionPopupDestroy();
    this.scheduleNowLine();
  }

  /**
   * Syncfusion instancia `quickPopup`/`eventWindow` en cada render, pero con
   * `prerenderDialogs=false` el `element` del EventWindow (editor) nunca se
   * crea. Al destruir el Schedule durante la navegación, `destroyPopups()`
   * llama a `eventWindow.destroy()` → `destroyComponents()` →
   * `getFormElements()`, que ejecuta `this.element.querySelectorAll(...)`
   * sobre un elemento nulo y lanza:
   *   TypeError: Cannot read properties of undefined (reading 'querySelectorAll')
   * Este Timeline nunca abre el editor nativo (se bloquea en onActionBegin /
   * openEditor), así que se envuelve `destroyPopups` con un guard try/catch
   * para que el teardown de la navegación no falle. El wrapper se aplica una
   * sola vez por instancia.
   */
  private guardSyncfusionPopupDestroy(): void {
    const schedule = this.hotelSchedule as unknown as {
      destroyPopups?: () => void;
      __popupDestroyGuarded?: boolean;
    } | undefined;
    if (!schedule || typeof schedule.destroyPopups !== 'function') return;
    if (schedule.__popupDestroyGuarded) return;
    const original = schedule.destroyPopups.bind(schedule);
    schedule.destroyPopups = (): void => {
      try {
        original();
      } catch {
        // Bug conocido de Syncfusion: popups del editor nunca renderizados
        // (prerenderDialogs=false) se destruyen con `element` nulo.
      }
    };
    schedule.__popupDestroyGuarded = true;
  }

  private disableNativeEditor(): void {
    const schedule = this.hotelSchedule;
    if (!schedule) return;
    schedule.openEditor = (): void => undefined;
  }

  /** Este Timeline no muestra ningún popup nativo de Syncfusion. */
  onPopupOpen(args: PopupOpenEventArgs): void {
    args.cancel = true;
  }

  /** Bloquea cualquier CRUD nativo aunque llegue por teclado o API. */
  onActionBegin(args: ActionEventArgs): void {
    if (args.requestType === 'eventCreate'
      || args.requestType === 'eventChange'
      || args.requestType === 'eventRemove') {
      args.cancel = true;
    }
  }

  /**
   * Al colapsar/expandir un nodo padre, Syncfusion oculta las filas con la
   * clase `e-hidden` en tres tablas a la vez (columna de recursos, cuadrícula
   * de días y tabla de eventos). Con agrupación anidada de 3 niveles
   * (Piso → Tipo → Habitación), su `updateContent` construye la lista de
   * filas de la cuadrícula con `querySelectorAll('.e-content-wrap tbody tr')`,
   * que mezcla las filas de la tabla de contenido con las de la tabla de
   * eventos; el mapeo por índice se descuadra y la columna de recursos
   * colapsa mientras la cuadrícula de días conserva sus filas (espacio en
   * blanco entre ambas columnas). Este self-heal re-aplica en la cuadrícula
   * y en los eventos exactamente las mismas filas `e-hidden` que quedaron en
   * la columna de recursos (fuente de verdad).
   */
  onActionComplete(args: ActionEventArgs): void {
    if (args.requestType === 'resourceCollapsed' || args.requestType === 'resourceExpanded') {
      this.syncCollapsedRows();
    }
  }

  /** Re-sincroniza las filas ocultas entre las tres tablas del Timeline. */
  private syncCollapsedRows(): void {
    const schedule = this.hotelSchedule;
    if (!schedule) return;
    const resourceRows = Array.from(schedule.element.querySelectorAll<HTMLTableRowElement>(
      '.e-resource-column-table tbody tr',
    ));
    if (resourceRows.length === 0) return;
    const contentRows = Array.from(schedule.element.querySelectorAll<HTMLTableRowElement>(
      '.e-content-table tbody tr',
    ));
    const eventRows = Array.from(schedule.element.querySelectorAll<HTMLTableRowElement>(
      '.e-event-table tbody tr',
    ));
    // `e-hidden` en el schedule es exclusivamente el mecanismo de colapso de
    // recursos; la columna de recursos (donde viven los iconos) es la fuente
    // de verdad. Cuando nada está colapsado el toggle simplemente limpia.
    resourceRows.forEach((row, index) => {
      const hidden = row.classList.contains('e-hidden');
      contentRows[index]?.classList.toggle('e-hidden', hidden);
      eventRows[index]?.classList.toggle('e-hidden', hidden);
    });
  }

  /** El Timeline nunca usa el editor nativo para crear reservas. */
  onCellDoubleClick(args: CellClickEventArgs): void {
    args.cancel = true;
  }

  /** Un doble clic sobre una reserva tampoco debe abrir edición inline. */
  onEventDoubleClick(args: EventClickArgs): void {
    args.cancel = true;
  }  onSelect(args: SelectEventArgs): void {
    if (args.requestType !== 'cellSelect') return;
    args.showQuickPopup = false;

    const schedule = this.hotelSchedule;
    if (!schedule) return;
    const eventElements = (Array.isArray(args.element) ? args.element : [args.element])
      .filter((element): element is HTMLElement => element instanceof HTMLElement);
    if (eventElements.length === 0) return;

    /*
     * Syncfusion emits `select` before it has finished applying
     * `.e-selected-cell` to every cell in a drag. Defer the read by two
     * animation frames so the panel uses the complete visual selection,
     * rather than only the last cell present in `args.element`.
     */
    if (this.cellSelectionFrame !== null) {
      cancelAnimationFrame(this.cellSelectionFrame);
    }
    this.cellSelectionFrame = requestAnimationFrame(() => {
      this.cellSelectionFrame = requestAnimationFrame(() => {
        this.cellSelectionFrame = null;
        this.processCellSelection(schedule, eventElements, args.groupIndex);
      });
    });
  }

  private processCellSelection(
    schedule: ScheduleComponent,
    eventElements: HTMLElement[],
    groupIndexHint?: number,
  ): void {
    const eventDetails = eventElements
      .map((element) => schedule.getCellDetails(element))
      .filter((detail) => detail !== null && detail !== undefined);
    if (eventDetails.length === 0) return;

    const groupIndex = groupIndexHint ?? eventDetails[0].groupIndex;
    if (groupIndex === undefined || groupIndex === null) return;

    /*
     * In a multi-cell drag Syncfusion may put only the last cell in
     * `args.element`, even though all cells already carry `.e-selected-cell`.
     * Reading the selected cells from the rendered Schedule prevents the
     * panel from collapsing a selection such as Aug 2–4 to only Aug 4.
     * Keep only the cells from the selected resource row; this avoids mixing
     * dates if another selection is still present while the event is emitted.
     */
    const selectedElements = Array.from(
      schedule.element.querySelectorAll('.e-selected-cell'),
    ).filter((element): element is HTMLElement => element instanceof HTMLElement)
      .filter((element) => schedule.getCellDetails(element)?.groupIndex === groupIndex);
    const elements = selectedElements.length > 0 ? selectedElements : eventElements;
    const details = elements
      .map((element) => schedule.getCellDetails(element))
      .filter((detail) => detail !== null && detail !== undefined);
    if (details.length === 0) return;

    const startTime = new Date(Math.min(...details.map((detail) => detail.startTime.getTime())));
    const endTime = new Date(Math.max(...details.map((detail) => detail.endTime.getTime())));
    const resourceDetails = schedule.getResourcesByIndex(groupIndex);
    const resource = resourceDetails?.resourceData as Record<string, unknown> | undefined;
    const roomId = String(resource?.['RoomId'] ?? '');
    const roomNumber = String(resource?.['RoomNumber'] ?? '');
    const roomTypeId = String(resource?.['RoomTypeValue'] ?? '');
    const roomTypeName = String(resource?.['RoomTypeName'] ?? '');
    if (!roomId || !roomNumber || roomId === 'UNASSIGNED' || !roomTypeId) {
      schedule.removeSelectedClass();
      return;
    }

    const today = this.toIsoDate(new Date());
    const includesPastDate = details.some((detail) => this.toIsoDate(detail.startTime) < today);
    if (includesPastDate) {
      schedule.removeSelectedClass();
      this.toast.warning('No puedes seleccionar fechas pasadas. Elige una fecha de hoy o futura.');
      return;
    }

    const selectionKey = `${roomId}:${startTime.getTime()}:${endTime.getTime()}`;
    if (this.selectedSlot() && this.lastCellSelectionKey === selectionKey) {
      this.dismissSelection();
      schedule.removeSelectedClass();
      return;
    }

    const selectedCells = elements.filter(
      (element): element is HTMLTableCellElement => element instanceof HTMLTableCellElement,
    );
    if (selectedCells.length > 0) {
      schedule.addSelectedClass(selectedCells, selectedCells[0], true);
    }

    const isDayCells = this.isDayCellSelection(details);
    this.lastCellSelectionKey = selectionKey;
    this.selectedSlot.set(this.buildSelection(
      roomId,
      roomNumber,
      roomTypeId,
      roomTypeName,
      startTime,
      endTime,
      isDayCells,
    ));
    this.scheduleSelectionPopoverPosition(elements);
  }

  dismissSelection(): void {
    this.selectedSlot.set(null);
    this.selectedAnchor = null;
    this.lastCellSelectionKey = '';
    this.selectionPopoverPosition.set({ top: 0, left: 0 });
  }

  async openPhysicalReservation(): Promise<void> {
    const selection = this.selectedSlot();
    if (!selection) return;

    // NavigationStart clears the mode owned by the current page. Re-claim it
    // only after the SPA navigation succeeds: at that point the destination
    // component and the shared OnPush nav are both alive, so the signal update
    // cannot be lost to the router's navigation lifecycle.
    let navigated: boolean;
    try {
      navigated = await this.router.navigate(['/management/recepcion/new'], {
        queryParams: {
        prop_id: this.propId(),
        room_type: selection.roomTypeId,
        room_type_name: selection.roomTypeName,
        hotel_room_id: selection.roomId,
        room_number: selection.roomNumber,
        check_in: selection.startDate,
        check_out: selection.endDate,
        check_in_time: selection.checkInTime,
        check_out_time: selection.checkOutTime,
      },
      });
    } catch {
      // A cancelled/rejected navigation must not leave the old page marked as
      // creating. The router owns the visible error/reporting path.
      return;
    }
    const currentPath = this.router.url.split('?')[0];
    if (!navigated || currentPath !== '/management/recepcion/new') return;
    // The destination route owns the page mode through its route metadata.
    // This component only performs navigation; it must not leave a transient
    // overlay alive after it is destroyed.
  }

  /**
   * True cuando cada celda seleccionada representa un día completo
   * (TimelineMonth). En ese caso check-in/check-out usan los horarios
   * estándar del hotel y el fin es el día siguiente al último día
   * seleccionado.
   */
  private isDayCellSelection(details: { startTime: Date; endTime: Date }[]): boolean {
    if (this.currentView() === 'TimelineMonth') return true;
    return details.every((detail) =>
      detail.startTime.getHours() === 0
      && detail.startTime.getMinutes() === 0
      && (detail.endTime.getTime() - detail.startTime.getTime()) >= 24 * 60 * 60 * 1000,
    );
  }

  /**
   * Construye el rango mostrado en el panel y enviado a la reserva física.
   *
   * - Celdas de día completo (Mes): check-in/check-out usan la política del
   *   hotel (``check_in_time``/``check_out_time``) y el fin es el día siguiente
   *   a la última celda seleccionada.
   * - Celdas por horas (Semana): conserva la hora exacta de la primera y la
   *   última celda; si el fin cae a medianoche se usa el check-out de la
   *   política del hotel. Una selección de horas del mismo día finaliza ese
   *   mismo día a la hora exacta de la última celda, sin arrastrar el check-out
   *   al día siguiente.
   */
  private buildSelection(
    roomId: string,
    roomNumber: string,
    roomTypeId: string,
    roomTypeName: string,
    startTime: Date,
    endTime: Date,
    isDayCells: boolean,
  ): TimelineSelection {
    const startDate = this.toIsoDate(startTime);
    if (isDayCells) {
      const lastDay = endTime.getTime() === startTime.getTime()
        ? startDate
        : this.toIsoDate(new Date(endTime.getTime() - 1));
      const normalizedEnd = lastDay <= startDate
        ? this.addDays(startDate, 1)
        : this.addDays(lastDay, 1);
      return {
        roomId,
        roomNumber,
        roomTypeId,
        roomTypeName,
        startDate,
        endDate: normalizedEnd,
        checkInTime: this.policyCheckInTime() || this.hourOfDay(startTime),
        checkOutTime: this.policyCheckOutTime() || this.hourOfDay(endTime),
      };
    }

    const endDateIso = this.toIsoDate(endTime);
    return {
      roomId,
      roomNumber,
      roomTypeId,
      roomTypeName,
      startDate,
      endDate: endDateIso <= startDate ? startDate : endDateIso,
      checkInTime: this.hourOfDay(startTime),
      checkOutTime: this.checkOutTimeFor(endTime),
    };
  }

  /** Hora exacta HH:MM de un Date; un check-in a medianoche se conserva. */
  private hourOfDay(date: Date): string {
    return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
  }

  /**
   * Hora de check-out: si el fin cae a medianoche (00:00) se normaliza al
   * check-out configurado en la política del hotel; cualquier otra hora se
   * conserva exacta.
   */
  private checkOutTimeFor(endTime: Date): string {
    if (endTime.getHours() === 0 && endTime.getMinutes() === 0) {
      return this.policyCheckOutTime() || this.hourOfDay(endTime);
    }
    return this.hourOfDay(endTime);
  }

  onEventClick(args: EventClickArgs): void {
    args.cancel = true;
    const event = (Array.isArray(args.event) ? args.event[0] : args.event) as unknown as TimelineEvent;
    if (!event) return;
    this.dismissSelection();
    this.selectedEvent.set(event);
    if (!event.BookingId) return;
    const reservation = this.calendarResource.value()?.rooms
      .flatMap((room) => room.reservations)
      .find((item) => item.bookingId === event.BookingId);
    if (reservation) this.reservationClick.emit(reservation);
  }

  reservationForEvent(event: TimelineEvent): ReceptionCalendarReservation {
    return {
      bookingId: event.BookingId,
      guestName: event.GuestName,
      adults: event.Adults,
      children: event.Children,
      checkInDate: event.CheckInDate,
      checkInTime: event.CheckInTime,
      estimatedArrivalTime: event.EstimatedArrivalTime || '',
      lateCheckin: !!event.LateCheckin,
      checkOutDate: event.CheckOutDate,
      checkOutTime: event.CheckOutTime,
      totalNights: event.TotalNights,
      status: event.VisualStatus,
      stayStatus: event.StayStatus || '',
      visualStatus: event.VisualStatus,
      reopenWindow: event.ReopenWindow ?? null,
      assignedRooms: event.RoomId === 'UNASSIGNED' ? [] : [event.RoomId],
      hotelRoomId: event.RoomId,
      roomNumber: event.RoomNumber,
      totalPrice: event.TotalPrice,
      currency: event.Currency,
    };
  }

  onEventRendered(args: EventRenderedArgs): void {
    const event = args.data as unknown as TimelineEvent;
    if (!event) return;
    if (!event.VisualStatus) return;

    // Mismo criterio que el SCSS .hotel-event-*: colores naturales de la app
    // (activa=azul primario, cancelada=rojo de la línea de tiempo) con su
    // texto semántico --on-* (blanco en light, oscuro en dark). past conserva
    // el gris oscurecido + blanco para contraste en ambos temas.
    const statusStyles: Record<ReceptionCalendarReservation['visualStatus'], {
      color: string;
      foreground: string;
    }> = {
      active: { color: 'var(--accent)', foreground: 'var(--on-accent)' },
      upcoming: { color: 'var(--warning)', foreground: 'var(--on-warning)' },
      past: { color: 'var(--muted-text)', foreground: 'var(--muted-text)' },
      cancelled: { color: 'var(--danger)', foreground: 'var(--on-danger)' },
    };
    const style = statusStyles[event.VisualStatus];
    if (!style) return;

    args.element.classList.add(`hotel-event-${event.VisualStatus}`);
    if (this.currentView() === 'TimelineMonth') {
      args.element.classList.add('timeline-appointment-stacked');
      // Syncfusion calculates the vertical lane offset before eventRendered
      // from the generic `.e-appointment` height. Keep the rendered node at
      // that same fixed height; otherwise its wrapped metadata grows past the
      // measured lane and concurrent reservations overlap visually.
      args.element.style.setProperty('height', MONTHLY_APPOINTMENT_HEIGHT, 'important');
      args.element.style.setProperty('min-height', MONTHLY_APPOINTMENT_HEIGHT, 'important');
    }
    const isPast = event.VisualStatus === 'past';
    args.element.style.setProperty(
      'background-color',
      isPast ? `color-mix(in srgb, ${style.color} 74%, #000)` : style.color,
    );
    args.element.style.setProperty('color', isPast ? '#fff' : style.foreground);
    if (event.VisualStatus === 'cancelled') args.element.style.opacity = '0.9';

    this.appendAppointmentMeta(args.element, event);
    this.appendLateCheckinMarker(args.element, event);
    this.appendNoShowMarker(args.element, event);
  }

  /**
   * Las reservas mensuales usan una segunda fila para los indicadores. Esto
   * conserva la información completa sin poner los iconos encima del nombre.
   */
  private isStackedAppointment(element: HTMLElement): boolean {
    return element.classList.contains('timeline-appointment-stacked');
  }

  private appendLateCheckinMarker(element: HTMLElement, event: TimelineEvent): void {
    if (!event.LateCheckin) return;
    if (element.querySelector('.timeline-late-marker')) return;
    const marker = document.createElement('span');
    marker.className = 'timeline-late-marker';
    marker.setAttribute('aria-label', 'Late check-in: llegada tarde');
    marker.title = 'Llegada tarde (late check-in)';
    const icon = document.createElement('span');
    icon.className = 'material-symbols-outlined';
    icon.setAttribute('aria-hidden', 'true');
    // `schedule` comunica hora de llegada; `nights_stay` queda reservado
    // exclusivamente para el número de noches.
    icon.textContent = 'schedule';
    marker.appendChild(icon);

    // En Mes, la marca comparte la fila inferior con personas/noches. En
    // Semana se conserva el comportamiento anterior dentro de la barra.
    const target = this.isStackedAppointment(element)
      ? element.querySelector<HTMLElement>('.timeline-app-meta') ?? element
      : element;
    target.appendChild(marker);
  }

  /**
   * Marca en la barra las reservas no-show: icono ``event_busy`` + clase
   * ``timeline-noshow-marker``. Cuando la ventana de reapertura está abierta
   * (check-in de hoy/ayer + estadía vigente) agrega ``is-reopenable`` (acento
   * ámbar + chip "Reabrible"); los antiguos quedan sin la marca de reapertura
   * para no invitar a una acción que la API rechazaría. ``ReopenWindow`` viene
   * del backend (server-authoritative, misma regla que ``reopen_no_show``).
   */
  private appendNoShowMarker(element: HTMLElement, event: TimelineEvent): void {
    if (event.StayStatus !== 'no_show') return;
    if (element.querySelector('.timeline-noshow-marker')) return;
    const reopenable = event.ReopenWindow === 'open';
    const marker = document.createElement('span');
    marker.className = 'timeline-noshow-marker' + (reopenable ? ' is-reopenable' : '');
    marker.setAttribute(
      'aria-label',
      reopenable
        ? 'No-show: reabrible dentro de la ventana (hoy o ayer con estadía vigente)'
        : 'No-show: ventana de reapertura cerrada',
    );
    marker.title = reopenable
      ? 'No-show — reabrible (hoy o ayer con estadía vigente)'
      : 'No-show — ventana de reapertura cerrada';
    const icon = document.createElement('span');
    icon.className = 'material-symbols-outlined';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = 'event_busy';
    marker.appendChild(icon);

    // En Mes la marca comparte la fila inferior con personas/noches; en
    // Semana se conserva dentro de la barra (mismo patrón que late check-in).
    const target = this.isStackedAppointment(element)
      ? element.querySelector<HTMLElement>('.timeline-app-meta') ?? element
      : element;
    target.appendChild(marker);
  }

  /**
   * Añade a la barra un chip resumen compacto con los ocupantes y noches:
   * noches = total de noches (incluye estancias de una sola noche). En Mes la fila puede
   * envolver para conservar todos los ítems aunque la celda sea estrecha.
   *
   * Validación anti-ambigüedad: NUNCA se muestran juntos el icono de persona
   * sola y el de grupo con el mismo número (dos iconos distintos diciendo
   * "2" se leerían como 4 personas). Regla: si hay niños o el total es >2
   * personas, se muestra solo el icono de grupo (adultos + niños); en caso
   * contrario (1-2 adultos sin niños) solo el de persona sola.
   */
  private appendAppointmentMeta(element: HTMLElement, event: TimelineEvent): void {
    if (element.querySelector('.timeline-app-meta')) return;
    const adults = Number(event.Adults) || 0;
    const children = Number(event.Children) || 0;
    const nights = Number(event.TotalNights) || 0;
    const total = adults + children;
    if (total <= 0 && nights <= 0) return;

    const meta = document.createElement('span');
    meta.className = 'timeline-app-meta';
    meta.setAttribute('aria-label', `${adults} adulto(s) · ${total} persona(s) · ${nights} noche(s)`);

    const item = (icon: string, count: number): HTMLSpanElement => {
      const span = document.createElement('span');
      span.className = 'timeline-app-meta-item';
      const iconEl = document.createElement('span');
      iconEl.className = 'material-symbols-outlined';
      iconEl.setAttribute('aria-hidden', 'true');
      iconEl.textContent = icon;
      span.append(iconEl);
      span.append(document.createTextNode(String(count)));
      return span;
    };

    const isGroup = total > 2 || children > 0;
    const personItem = isGroup ? null : item('person', adults);
    const groupItem = isGroup ? item('group', total) : null;
    if (personItem) meta.append(personItem);
    if (groupItem) meta.append(groupItem);
    if (nights > 0) {
      meta.append(item('nights_stay', nights));
    }

    // En Mes la meta se coloca en una fila inferior de la misma barra; en
    // Semana conserva su posición flotante original mediante sus estilos.
    element.appendChild(meta);

    // La actualización se difiere dos frames para que Syncfusion haya
    // terminado de dimensionar la barra antes de limpiar cualquier estado
    // residual.
    requestAnimationFrame(() => {
      requestAnimationFrame(() => this.applyMetaDisclosure(element));
    });
    element.setAttribute('title', `${event.GuestName} · ${event.StatusLabel}`);
  }

  /**
   * Mantiene la información completa de la barra. Antes se ocultaban los
   * indicadores por umbrales de ancho; en la vista mensual ahora se apilan y
   * pueden envolver en varias líneas cuando la celda es estrecha.
   */
  private applyMetaDisclosure(element: HTMLElement): void {
    const meta = element.querySelector<HTMLElement>('.timeline-app-meta');
    if (!meta) return;
    meta.classList.remove('timeline-app-meta--hidden');
    meta.querySelectorAll<HTMLElement>('.timeline-app-meta-item')
      .forEach((item) => item.classList.remove('timeline-app-meta-item--hidden'));
  }

  private scheduleSelectionPopoverPosition(element: HTMLElement | HTMLElement[]): void {
    if (this.selectionPositionFrame !== null) {
      cancelAnimationFrame(this.selectionPositionFrame);
    }
    this.selectionPositionFrame = requestAnimationFrame(() => {
      this.selectionPositionFrame = requestAnimationFrame(() => {
        this.selectionPositionFrame = null;
        if (this.selectedSlot()) this.positionSelectionPopover(element);
      });
    });
  }

  private positionSelectionPopover(element: HTMLElement | HTMLElement[]): void {
    const anchor = Array.isArray(element) ? element[0] : element;
    if (!anchor) return;
    this.selectedAnchor = anchor;
    const rect = anchor.getBoundingClientRect();
    const panelWidth = Math.min(440, window.innerWidth - 24);
    const panelHeight = this.selectionPopover?.nativeElement.offsetHeight
      || (window.innerWidth <= 700 ? 132 : 116);
    const gap = 8;
    const left = Math.max(12, Math.min(rect.left, window.innerWidth - panelWidth - 12));
    const below = rect.bottom + gap;
    const top = below + panelHeight <= window.innerHeight - 12
      ? below
      : Math.max(12, rect.top - panelHeight - gap);
    this.selectionPopoverPosition.set({ top, left });
  }

  closeDetail(): void {
    this.selectedEvent.set(null);
  }

  resourceHeaderKind(data: unknown): 'floor' | 'roomType' | 'room' {
    const context = data as {
      resourceData?: Record<string, unknown>;
      resource?: { name?: string; textField?: string };
    };
    const resourceData = context.resourceData ?? {};
    const explicitKind = resourceData['ResourceKind'] ?? resourceData['ResourceLevel'];
    if (explicitKind === 'floor' || explicitKind === 'roomType' || explicitKind === 'room') {
      return explicitKind;
    }

    const textField = context.resource?.textField;
    if (textField === 'FloorName') return 'floor';
    if (textField === 'RoomTypeName') return 'roomType';
    if (textField === 'RoomNumber') return 'room';

    const resourceName = context.resource?.name;
    if (resourceName === 'Floors') return 'floor';
    if (resourceName === 'RoomTypes') return 'roomType';
    return 'room';
  }

  resourceHeaderText(data: unknown): string {
    const context = data as {
      resourceData?: Record<string, unknown>;
      resource?: { textField?: string };
      resourceName?: string;
    };
    const resourceData = context.resourceData ?? {};
    const textField = context.resource?.textField;
    const candidates = [
      textField ? resourceData[textField] : undefined,
      resourceData['DisplayName'],
      resourceData['FloorName'],
      resourceData['RoomTypeName'],
      resourceData['RoomNumber'],
      context.resourceName,
    ];

    for (const candidate of candidates) {
      if (typeof candidate === 'string' && !this.isMissingValue(candidate)) return candidate.trim();
    }

    return this.resourceHeaderKind(data) === 'floor'
      ? 'Piso'
      : this.resourceHeaderKind(data) === 'roomType' ? 'Tipo de habitación' : 'Habitación';
  }

  operationalStatusLabel(roomId: string): string {
    const status = this.roomStatuses().get(roomId)?.status;
    if (!status || this.isMissingValue(status)) return '';
    return ROOM_STATUS_LABELS[status] ?? status;
  }

  operationalStatusColor(roomId: string): string {
    return roomStatusColor(this.roomStatuses().get(roomId)?.status ?? '');
  }

  statusLabel(status: ReceptionCalendarReservation['visualStatus']): string {
    switch (status) {
      case 'active': return 'Vigente';
      case 'upcoming': return 'Próxima';
      case 'past': return 'Finalizada';
      case 'cancelled': return 'Cancelada';
      default: return 'Sin estado';
    }
  }

  private displayValue(value: string | null | undefined, fallback: string): string {
    return this.isMissingValue(value) ? fallback : value.trim();
  }

  private isMissingValue(value: string | null | undefined): value is null | undefined | '' {
    if (value === null || value === undefined) return true;
    const normalized = value.trim().toLowerCase();
    return normalized === '' || normalized === 'undefined' || normalized === 'null';
  }

  private floorResourceId(floor: string): string {
    return `floor:${this.displayValue(floor, 'unknown')}`;
  }

  private roomTypeResourceId(room: ReceptionCalendarData['rooms'][number]): string {
    return `type:${this.displayValue(room.floor, 'unknown')}:${this.displayValue(room.roomTypeId, 'unknown')}`;
  }

  private roomColor(roomTypeId: string): string {
    const palette = [
      'var(--accent)',
      'var(--success)',
      'var(--warning)',
      'var(--accent-strong)',
      'var(--info, var(--accent))',
    ];
    let hash = 0;
    for (const character of roomTypeId) hash = (hash * 31 + character.charCodeAt(0)) | 0;
    return palette[Math.abs(hash) % palette.length];
  }

  /**
   * Construye un Date para renderizar un evento. El fallback 12:00 es solo un
   * guard de parseo para reservas con hora ausente/malformada; los horarios de
   * negocio (prefill de nueva reserva) provienen de la política del hotel.
   */
  private toDate(date: string, time: string): Date {
    return new Date(`${date}T${time || '12:00'}:00`);
  }

  private weekStart(date: Date): Date {
    const result = new Date(date);
    const day = result.getDay();
    result.setDate(result.getDate() - day + (day === 0 ? -6 : 1));
    result.setHours(12, 0, 0, 0);
    return result;
  }

  private toIsoDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  private addDays(date: string, days: number): string {
    const result = new Date(`${date}T12:00:00`);
    result.setDate(result.getDate() + days);
    return this.toIsoDate(result);
  }

  private addMonths(date: string, months: number): string {
    const result = new Date(`${date}T12:00:00`);
    result.setMonth(result.getMonth() + months, 1);
    return this.toIsoDate(result);
  }

  private monthStart(date: Date): Date {
    const result = new Date(date);
    result.setDate(1);
    result.setHours(12, 0, 0, 0);
    return result;
  }

  private monthGridStart(date: Date): Date {
    const result = this.monthStart(date);
    const day = result.getDay();
    result.setDate(result.getDate() - (day === 0 ? 6 : day - 1));
    return result;
  }

  private monthGridEnd(date: Date): Date {
    const result = this.monthStart(date);
    result.setMonth(result.getMonth() + 1, 0);
    const day = result.getDay();
    result.setDate(result.getDate() + (day === 0 ? 0 : 7 - day));
    return result;
  }
}
