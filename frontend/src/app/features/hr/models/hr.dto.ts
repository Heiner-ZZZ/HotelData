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
  is_active: boolean;
  created_at: string;
  updated_at: string;
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

export interface ShiftCheckInDto {
  employee_id: string;
  timestamp?: string;
  notes?: string;
}

export interface ShiftCheckOutDto {
  employee_id: string;
  timestamp?: string;
  notes?: string;
}
