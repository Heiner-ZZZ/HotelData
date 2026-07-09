import type {
  EmployeeDetailDto, EmployeeItemDto, EmployeeListDto, HrDashboardDto,
  EmployeePortalDto, EmployeeShiftDto, EmployeeKpiDto,
  WeeklyRosterEntryDto, PayrollDto, TimelineEventDto,
} from '../models/hr.dto';
import type {
  EmployeeDetail, EmployeeListItem, HrDashboard,
  EmployeePortal, EmployeeShift, EmployeeKpis,
  WeeklyRosterEntry, Payroll, TimelineEvent,
} from '../models/hr.model';

function mapEmployeeItem(dto: EmployeeItemDto): EmployeeListItem {
  return {
    id: dto.id,
    fullName: dto.full_name,
    idDocument: dto.id_document,
    phone: dto.phone,
    email: dto.email,
    position: dto.position,
    department: dto.department,
    isActive: dto.is_active,
    hireDate: dto.hire_date,
    createdAt: dto.created_at,
  };
}

export function mapEmployeeList(dto: EmployeeListDto) {
  return {
    items: dto.items.map(mapEmployeeItem),
    total: dto.total,
    page: dto.page,
    pageSize: dto.page_size,
    totalPages: dto.total_pages,
    hasNext: dto.has_next,
    hasPrev: dto.has_prev,
  };
}

export function mapEmployeeDetail(dto: EmployeeDetailDto): EmployeeDetail {
  return {
    id: dto.id,
    fullName: dto.full_name,
    idDocument: dto.id_document,
    phone: dto.phone,
    email: dto.email,
    address: dto.address,
    position: dto.position,
    department: dto.department,
    hireDate: dto.hire_date,
    salary: dto.salary,
    emergencyContact: dto.emergency_contact,
    emergencyPhone: dto.emergency_phone,
    notes: dto.notes,
    propId: dto.prop_id,
    userId: dto.user_id ?? null,
    isActive: dto.is_active,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

export function mapHrDashboard(dto: HrDashboardDto): HrDashboard {
  return {
    totalEmployees: dto.total_employees,
    activeEmployees: dto.active_employees,
    inactiveEmployees: dto.inactive_employees,
    departments: dto.departments,
    recentHires: (dto.recent_hires || []).map(mapEmployeeItem),
  };
}

// ─── Portal mappers ───

function mapShift(dto: EmployeeShiftDto): EmployeeShift {
  return {
    id: dto.id,
    employeeId: dto.employee_id,
    date: dto.date,
    scheduledStart: dto.scheduled_start,
    scheduledEnd: dto.scheduled_end,
    area: dto.area,
    status: dto.status,
    actualCheckIn: dto.actual_check_in,
    actualCheckOut: dto.actual_check_out,
    notes: dto.notes,
    createdAt: dto.created_at,
  };
}

function mapKpis(dto: EmployeeKpiDto): EmployeeKpis {
  return {
    sales: dto.sales,
    salesFormatted: dto.sales_formatted,
    payments: dto.payments,
    upsells: dto.upsells,
    upsellsTarget: dto.upsells_target,
  };
}

function mapRosterEntry(dto: WeeklyRosterEntryDto): WeeklyRosterEntry {
  return {
    date: dto.date,
    day: dto.day,
    dayNumber: dto.day_number,
    month: dto.month,
    isToday: dto.is_today,
    shiftStart: dto.shift_start,
    shiftEnd: dto.shift_end,
    area: dto.area,
    status: dto.status,
  };
}

function mapPayroll(dto: PayrollDto): Payroll {
  return {
    workedHours: dto.worked_hours,
    targetHours: dto.target_hours,
    progressPct: dto.progress_pct,
    periodLabel: dto.period_label,
  };
}

function mapTimelineEvent(dto: TimelineEventDto): TimelineEvent {
  return {
    type: dto.type,
    label: dto.label,
    detail: dto.detail,
    timestamp: dto.timestamp,
    icon: dto.icon,
  };
}

export function mapEmployeePortal(dto: EmployeePortalDto): EmployeePortal {
  return {
    employee: mapEmployeeDetail(dto.employee),
    currentShift: dto.current_shift ? mapShift(dto.current_shift) : null,
    kpis: mapKpis(dto.kpis),
    weeklyRoster: (dto.weekly_roster || []).map(mapRosterEntry),
    payroll: mapPayroll(dto.payroll),
    recentEvents: (dto.recent_events || []).map(mapTimelineEvent),
  };
}
