export interface DepartmentDto {
  id: string;
  name: string;
  description: string;
  head_count: number;
  created_at: string;
}

export interface DepartmentListDto {
  items: DepartmentDto[];
  total: number;
}

export interface ReplacementCandidateDto {
  id: string;
  full_name: string;
  department: string;
  position: string;
  shift_count: number;
  permission_count: number;
  task_count: number;
  duty_count: number;
}

export interface ReplacementCandidateListDto {
  items: ReplacementCandidateDto[];
  total: number;
}

export interface EmployeeListDto {
  items: EmployeeItemDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface EmployeeItemDto {
  id: string;
  full_name: string;
  id_document: string;
  phone: string;
  email: string;
  position: string;
  department: string;
  is_active: boolean;
  hire_date: string;
  created_at: string;
}

export interface EmployeeCreateDto {
  full_name: string;
  id_document: string;
  phone?: string;
  email?: string;
  address?: string;
  position?: string;
  department?: string;
  hire_date?: string;
  salary?: number | null;
  emergency_contact?: string;
  emergency_phone?: string;
  notes?: string;
  prop_id?: number | null;
  user_id?: string | null;
  daily_duties?: unknown[] | null;
  replaces_employee_id?: string | null;
  transfer_shifts?: boolean;
  transfer_permissions?: boolean;
  transfer_tasks?: boolean;
}

export interface EmployeeUpdateDto {
  full_name?: string;
  phone?: string;
  email?: string;
  address?: string;
  position?: string;
  department?: string;
  salary?: number | null;
  emergency_contact?: string;
  emergency_phone?: string;
  notes?: string;
  is_active?: boolean;
  user_id?: string | null;
  daily_duties?: unknown[];
}

export interface EmployeeDetailDto {
  id: string;
  full_name: string;
  id_document: string;
  phone: string;
  email: string;
  address: string;
  position: string;
  department: string;
  hire_date: string;
  salary: number | null;
  emergency_contact: string;
  emergency_phone: string;
  notes: string;
  prop_id: number | null;
  user_id: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  username?: string;
  password?: string | null;
}

export interface HrDashboardDto {
  total_employees: number;
  active_employees: number;
  inactive_employees: number;
  departments: number;
  recent_hires: EmployeeItemDto[];
}

// ─── Portal (Employee Dashboard) ───

export interface EmployeePortalDto {
  employee: EmployeeDetailDto;
  current_shift: EmployeeShiftDto | null;
  kpis: EmployeeKpiDto;
  weekly_roster: WeeklyRosterEntryDto[];
  payroll: PayrollDto;
  recent_events: TimelineEventDto[];
}

export interface EmployeeShiftDto {
  id: string;
  employee_id: string;
  date: string;
  scheduled_start: string;
  scheduled_end: string;
  area: string;
  status: 'pending' | 'active' | 'completed' | 'rest';
  actual_check_in: string | null;
  actual_check_out: string | null;
  notes: string;
  created_at: string;
}

export interface EmployeeKpiDto {
  sales: number;
  sales_formatted: string;
  payments: number;
  upsells: number;
  upsells_target: number;
}

export interface WeeklyRosterEntryDto {
  date: string;
  day: string;
  day_number: number;
  month: number;
  is_today: boolean;
  shift_start: string;
  shift_end: string;
  area: string;
  status: string;
  actual_check_in: string | null;
  actual_check_out: string | null;
}

export interface PayrollDto {
  worked_hours: number;
  target_hours: number;
  progress_pct: number;
  period_label: string;
}

export interface TimelineEventDto {
  type: string;
  label: string;
  detail: string;
  timestamp: string;
  icon: string;
}

export interface AttendanceRecordDto {
  date: string;
  day_name: string;
  shift_start: string;
  shift_end: string;
  check_in: string | null;
  check_out: string | null;
  hours_worked: number | null;
  status: string;
  area: string;
}

export interface AttendanceSummaryDto {
  total_days: number;
  days_worked: number;
  total_hours: number;
  avg_hours_per_day: number;
  on_time_percentage: number;
  month: string;
}

export interface AttendanceResponseDto {
  employee_id: string;
  employee_name: string;
  month: string;
  records: AttendanceRecordDto[];
  summary: AttendanceSummaryDto;
}

export interface ShiftItemDto {
  id: string;
  employee_id: string;
  date: string;
  scheduled_start: string;
  scheduled_end: string;
  area: string;
  status: string;
  actual_check_in: string | null;
  actual_check_out: string | null;
  notes: string;
  employee_name?: string;
}

export interface ShiftListDto {
  items: ShiftItemDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ShiftCreateDto {
  employee_id: string;
  date: string;
  scheduled_start: string;
  scheduled_end: string;
  area?: string;
  notes?: string;
}

// ─── Portal Tasks & Operations ───

export interface PortalTaskDto {
  id: string;
  type: 'cleaning' | 'maintenance';
  room_label: string;
  task_type: string;
  title?: string;
  status: string;
  priority: string;
  note: string;
  scheduled_date: string;
  created_at: string;
}

export interface DirtyRoomDto {
  room_label: string;
  room_number: string;
  status: string;
  floor: string;
  note: string;
}

export interface DailyDutyDto {
  label: string;
  icon: string;
  description?: string;
}

export interface PortalTasksDto {
  employee_id: string;
  employee_name: string;
  assigned_tasks: PortalTaskDto[];
  dirty_rooms: DirtyRoomDto[];
  daily_duties: DailyDutyDto[];
}
