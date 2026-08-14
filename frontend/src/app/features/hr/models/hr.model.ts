export interface EmployeeListItem {
  id: string;
  fullName: string;
  idDocument: string;
  phone: string;
  email: string;
  position: string;
  department: string;
  isActive: boolean;
  hireDate: string;
  createdAt: string;
  /** true si el empleado tiene user_id que resuelve a un users._id vivo. */
  hasUserAccount: boolean;
  /** true si su cuenta tiene un hotel_role asignado en el prop_id del empleado. */
  roleAssigned: boolean;
}

export interface EmployeeDetail {
  id: string;
  fullName: string;
  idDocument: string;
  phone: string;
  email: string;
  address: string;
  position: string;
  department: string;
  hireDate: string;
  salary: number | null;
  emergencyContact: string;
  emergencyPhone: string;
  notes: string;
  propId: number | null;
  userId: string | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
  username?: string;
  password?: string | null;
}

export interface HrDashboard {
  totalEmployees: number;
  activeEmployees: number;
  inactiveEmployees: number;
  departments: number;
  recentHires: EmployeeListItem[];
}

// ─── Portal (Employee Dashboard) ───

export interface EmployeePortal {
  employee: EmployeeDetail;
  currentShift: EmployeeShift | null;
  kpis: EmployeeKpis;
  weeklyRoster: WeeklyRosterEntry[];
  payroll: Payroll;
  recentEvents: TimelineEvent[];
}

export interface EmployeeShift {
  id: string;
  employeeId: string;
  date: string;
  scheduledStart: string;
  scheduledEnd: string;
  area: string;
  status: 'pending' | 'active' | 'completed' | 'rest';
  actualCheckIn: string | null;
  actualCheckOut: string | null;
  notes: string;
  createdAt: string;
}

export interface EmployeeKpis {
  sales: number;
  salesFormatted: string;
  payments: number;
  upsells: number;
  upsellsTarget: number;
}

export interface WeeklyRosterEntry {
  date: string;
  day: string;
  dayNumber: number;
  month: number;
  isToday: boolean;
  shiftStart: string;
  shiftEnd: string;
  area: string;
  status: string;
  actualCheckIn: string | null;
  actualCheckOut: string | null;
}

export interface Payroll {
  workedHours: number;
  targetHours: number;
  progressPct: number;
  periodLabel: string;
}

export interface TimelineEvent {
  type: string;
  label: string;
  detail: string;
  timestamp: string;
  icon: string;
}

// ─── Attendance History ───

export interface AttendanceRecord {
  date: string;
  dayName: string;
  shiftStart: string;
  shiftEnd: string;
  checkIn: string | null;
  checkOut: string | null;
  hoursWorked: number | null;
  status: string;
  area: string;
}

export interface AttendanceSummary {
  totalDays: number;
  daysWorked: number;
  totalHours: number;
  avgHoursPerDay: number;
  onTimePercentage: number;
  month: string;
}

export interface AttendanceResponse {
  employeeId: string;
  employeeName: string;
  month: string;
  records: AttendanceRecord[];
  summary: AttendanceSummary;
}

// ─── Shift Schedule ───

export interface ShiftItem {
  id: string;
  employeeId: string;
  date: string;
  scheduledStart: string;
  scheduledEnd: string;
  area: string;
  status: string;
  actualCheckIn: string | null;
  actualCheckOut: string | null;
  notes: string;
  employeeName?: string;
}

export interface ShiftList {
  items: ShiftItem[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

export interface ShiftCreatePayload {
  employeeId: string;
  date: string;
  scheduledStart: string;
  scheduledEnd: string;
  area?: string;
  notes?: string;
}

// ─── Portal Tasks & Operations ───

export interface PortalTask {
  id: string;
  type: 'cleaning' | 'maintenance';
  roomLabel: string;
  taskType: string;
  title?: string;
  status: string;
  priority: string;
  note: string;
  scheduledDate: string;
  createdAt: string;
}

export interface DirtyRoom {
  roomLabel: string;
  roomNumber: string;
  status: string;
  floor: string;
  note: string;
}

export interface DailyDuty {
  label: string;
  icon: string;
  description?: string;
}

export interface PortalTasksData {
  employeeId: string;
  employeeName: string;
  assignedTasks: PortalTask[];
  dirtyRooms: DirtyRoom[];
  dailyDuties: DailyDuty[];
}
