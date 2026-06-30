import { DatePipe, KeyValuePipe, TitleCasePipe } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, computed, inject, signal,
} from '@angular/core';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { lastValueFrom } from 'rxjs';

import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { HousekeepingSubNavComponent } from '../../components/housekeeping-sub-nav/housekeeping-sub-nav';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import {
  HousekeepingApiService,
  type CalendarDayTask,
  type CalendarRoomDay,
  type WeeklyCalendarData,
} from '../../services/housekeeping-api.service';

/** Generate ISO date string for today (local timezone-aware). */
function todayIso(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

/** Get Monday of the week containing the given date. */
function getWeekStart(dateStr: string): string {
  const d = new Date(dateStr + 'T12:00:00');
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  d.setDate(diff);
  return d.toISOString().slice(0, 10);
}

/** Add N weeks to a date string. */
function addWeeks(dateStr: string, weeks: number): string {
  const d = new Date(dateStr + 'T12:00:00');
  d.setDate(d.getDate() + weeks * 7);
  return d.toISOString().slice(0, 10);
}

/** Day name in Spanish. */
const DAY_NAMES = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

/** Task type labels. */
const TASK_TYPE_LABELS: Record<string, string> = {
  cleaning: 'Limpieza',
  deep_clean: 'Limp. Profunda',
  turnover: 'Rotación',
  inspection: 'Inspección',
  maintenance: 'Mantenimiento',
};

/** Task type icons. */
const TASK_TYPE_ICONS: Record<string, string> = {
  cleaning: 'cleaning_services',
  deep_clean: 'auto_awesome',
  turnover: 'sync',
  inspection: 'visibility',
  maintenance: 'build',
};

/** Status colors for task badges. */
const TASK_STATUS_COLORS: Record<string, string> = {
  pending: '#d97706',
  in_progress: '#006076',
  inspection: '#7c3aed',
  completed: '#059669',
  scheduled: '#ea580c',
  maintenance: '#ba1a1a',
};

/** Common staff names. */
const COMMON_STAFF = [
  'María García', 'Juan Pérez', 'Ana López', 'Carlos Ruiz',
  'Sofía Martínez', 'Pedro Hernández', 'Laura Sánchez', 'Miguel Torres',
  'Gabriela Flores', 'Diego Ramírez',
];

@Component({
  selector: 'app-housekeeping-calendar-page',
  imports: [DatePipe, KeyValuePipe, TitleCasePipe, ReactiveFormsModule, PropertySelectorComponent, HousekeepingSubNavComponent, EmptyStateComponent, ErrorStateComponent, LoadingStateComponent],
  templateUrl: './housekeeping-calendar-page.html',
  styleUrl: './housekeeping-calendar-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HousekeepingCalendarPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(HousekeepingApiService);
  private readonly fb = inject(FormBuilder);
  private readonly propertyCtx = inject(PropertyContextService);

  // ── Week navigation ──
  readonly weekStart = signal(getWeekStart(todayIso()));
  readonly today = todayIso();

  // ── Filters ──
  readonly assignedToFilter = signal('');

  // ── Prop ID from URL ──
  private readonly qp = toSignal(this.route.queryParamMap, { initialValue: this.route.snapshot.queryParamMap });
  readonly selectedPropId = computed(() => Number(this.qp()?.get('prop_id') ?? '0'));
  readonly selectedLabel = signal(this.route.snapshot.queryParamMap.get('prop_label') ?? '');

  // ── Calendar resource ──
  readonly calendarResource = rxResource<any, any>({
    params: () => {
      const pid = this.selectedPropId();
      if (!pid) return undefined;
      return {
        propId: pid,
        weekStart: this.weekStart(),
        assignedTo: this.assignedToFilter() || undefined,
      };
    },
    stream: ({ params }) =>
      this.api.getWeeklyCalendar((params as any).propId, (params as any).weekStart, (params as any).assignedTo),
  });

  readonly calendarData = computed(() => this.calendarResource.value() ?? null);

  readonly viewState = computed(() => {
    const r = this.calendarResource;
    if (r.isLoading() || r.status() === 'idle') return 'loading';
    if (r.error()) return 'error';
    const d = r.value();
    if (!d || !d.week_days.length) return 'empty';
    return 'success';
  });

  readonly weekDays = computed(() => this.calendarData()?.week_days ?? []);
  readonly rooms = computed(() => {
    const cal = this.calendarData()?.calendar;
    if (!cal) return [] as CalendarRoomDay[];
    return Object.values(cal) as CalendarRoomDay[];
  });
  readonly staffList = computed(() => this.calendarData()?.staff ?? []);
  readonly summary = computed(() => this.calendarData()?.summary ?? { total_tasks: 0, by_status: {} });

  // ── Quick create form ──
  readonly showQuickForm = signal(false);
  readonly quickFormTarget = signal<{ roomLabel: string; date: string } | null>(null);
  readonly quickFormBusy = signal(false);

  readonly quickForm = this.fb.nonNullable.group({
    taskType: ['cleaning', Validators.required],
    assignedTo: [''],
    priority: ['normal'],
    note: [''],
  });

  // ── Display helpers ──
  readonly dayNames = DAY_NAMES;
  readonly taskTypeLabels = TASK_TYPE_LABELS;
  readonly taskTypeIcons = TASK_TYPE_ICONS;
  readonly taskStatusColors = TASK_STATUS_COLORS;
  readonly commonStaff = COMMON_STAFF;

  // ── Property selection ──
  onPropSelected(event: { propId: number; label: string }): void {
    const label = event.label || `Propiedad #${event.propId}`;
    this.selectedLabel.set(label);
    if (event.propId) {
      this.propertyCtx.setProperty(event.propId, label);
    } else {
      this.propertyCtx.clear();
    }
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null, prop_label: label || null },
      queryParamsHandling: 'merge',
    });
  }

  // ── Week navigation ──
  prevWeek(): void {
    this.weekStart.set(addWeeks(this.weekStart(), -1));
  }

  nextWeek(): void {
    this.weekStart.set(addWeeks(this.weekStart(), +1));
  }

  goToday(): void {
    this.weekStart.set(getWeekStart(todayIso()));
  }

  // ── Staff filter ──
  setStaffFilter(staff: string): void {
    this.assignedToFilter.set(staff === this.assignedToFilter() ? '' : staff);
  }

  // ── Quick create ──
  openQuickForm(roomLabel: string, date: string): void {
    this.quickFormTarget.set({ roomLabel, date });
    this.quickForm.reset({ taskType: 'cleaning', assignedTo: '', priority: 'normal', note: '' });
    this.showQuickForm.set(true);
  }

  closeQuickForm(): void {
    this.showQuickForm.set(false);
    this.quickFormTarget.set(null);
  }

  async submitQuickTask(): Promise<void> {
    if (this.quickForm.invalid) return;
    const target = this.quickFormTarget();
    if (!target) return;
    const val = this.quickForm.getRawValue();

    this.quickFormBusy.set(true);
    try {
      await lastValueFrom(this.api.createTask({
        prop_id: this.selectedPropId(),
        room_label: target.roomLabel,
        task_type: val.taskType,
        assigned_to: val.assignedTo || undefined,
        priority: val.priority,
        note: val.note || undefined,
        scheduled_date: target.date,
      }));
      this.closeQuickForm();
      this.calendarResource.reload();
    } catch {
      // error silently — the task list will show errors if needed
    } finally {
      this.quickFormBusy.set(false);
    }
  }

  // ── Format helpers ──
  formatDayHeader(dateStr: string): { dayName: string; dayNum: string; isToday: boolean } {
    const d = new Date(dateStr + 'T12:00:00');
    const dayOfWeek = d.getDay();
    const dayName = DAY_NAMES[dayOfWeek === 0 ? 6 : dayOfWeek - 1];
    const dayNum = String(d.getDate()).padStart(2, '0');
    const isToday = dateStr === this.today;
    return { dayName, dayNum, isToday };
  }

  /** Get the month label for the week (e.g., "Junio 2026"). */
  getMonthLabel(): string {
    const days = this.weekDays();
    if (!days.length) return '';
    const start = new Date(days[0] + 'T12:00:00');
    const end = new Date(days[days.length - 1] + 'T12:00:00');
    const months = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
    const startMonth = months[start.getMonth()];
    const endMonth = months[end.getMonth()];
    if (start.getMonth() === end.getMonth()) {
      return `${startMonth} ${start.getFullYear()}`;
    }
    return `${startMonth} → ${endMonth} ${end.getFullYear()}`;
  }

  /** Human-readable week range. */
  getWeekRange(): string {
    const days = this.weekDays();
    if (days.length < 2) return '';
    const fmt = (s: string) => {
      const d = new Date(s + 'T12:00:00');
      return `${String(d.getDate()).padStart(2, '0')}/${String(d.getMonth() + 1).padStart(2, '0')}`;
    };
    return `${fmt(days[0])} — ${fmt(days[days.length - 1])}`;
  }

  /** Count tasks in a day cell. */
  taskCount(tasks: CalendarDayTask[] | undefined): number {
    return tasks?.length ?? 0;
  }

  /** Get task type color for the cell indicator. */
  getTaskType(task: CalendarDayTask): string {
    return TASK_STATUS_COLORS[task.status] ?? TASK_STATUS_COLORS[task.task_type] ?? '#6f797d';
  }

  /** Priority class. */
  priorityClass(p: string): string { return `prio-${p}`; }
}
