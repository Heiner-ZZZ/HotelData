import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

export interface RoomStatusItem {
  id: string;
  propId: number;
  roomTypeId: string;
  roomLabel: string;
  roomNumber: string;
  hotelRoomId: string;
  status: string;
  note: string;
  createdAt: string;
  updatedAt: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

export interface HousekeepingTaskItem {
  id: string;
  propId: number;
  roomId: string;
  roomLabel: string;
  roomTypeId: string;
  roomNumber: string;
  taskType: string;
  status: string;
  assignedTo: string;
  priority: string;
  note: string;
  scheduledDate: string;
  createdAt: string;
  completedAt: string | null;
}

export interface MaintenanceTaskItem {
  id: string;
  propId: number;
  roomId: string;
  roomLabel: string;
  roomTypeId: string;
  roomNumber: string;
  taskType: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  scheduledDate: string;
  autoBlock: boolean;
  createdAt: string;
  completedAt: string | null;
}

export interface StaffUser {
  username: string;
  display_name: string;
  email: string;
  primary_role: string;
  assigned_hotels: number[];
}

export interface RoomStatusHistoryEntry {
  id: string;
  propId: number;
  roomLabel: string;
  oldStatus: string;
  newStatus: string;
  note: string;
  changedBy: string;
  bookingId: string;
  createdAt: string;
}

export interface AdditionalChargeItem {
  id: string;
  bookingId: string;
  propId: number;
  concept: string;
  amount: number;
  quantity: number;
  total: number;
  note: string;
  createdAt: string;
  chargeDate: string;
}

export interface DashboardRoomItem {
  id: string;
  propId: number;
  roomLabel: string;
  roomNumber: string;
  hotelRoomId: string;
  roomTypeId: string;
  status: string;
  statusLabel: string;
  statusColor: string;
  note: string;
  createdAt: string;
  updatedAt: string | null;
  cleaning_started_at?: string;
  cleaning_completed_at?: string;
}

export interface FloorData {
  floor: string;
  rooms: DashboardRoomItem[];
  count: number;
  status_counts: Record<string, number>;
}

export interface CalendarDayTask {
  id: string;
  task_type: string;
  status: string;
  assigned_to: string;
  priority: string;
  note: string;
  scheduled_date: string;
  title?: string;
  description?: string;
}

export interface CalendarRoomDay {
  room_id: string;
  room_label: string;
  room_number: string;
  status: string;
  status_color: string;
  status_label: string;
  days: Record<string, CalendarDayTask[]>;
}

export interface WeeklyCalendarData {
  week_days: string[];
  week_start: string;
  week_end: string;
  calendar: Record<string, CalendarRoomDay>;
  staff: string[];
  summary: {
    total_tasks: number;
    by_status: Record<string, number>;
  };
}

export interface HousekeepingDashboard {
  totalRooms: number;
  occupied: number;
  vacant: number;
  clean_rooms: number;
  pending_rooms: number;
  in_cleaning: number;
  cleaning_completed: number;
  inspected: number;
  out_of_service: number;
  out_of_order: number;
  maintenance_requested: number;
  occupancyRate: number;
  roomStatuses: Record<string, number>;
  status_labels: Record<string, string>;
  status_colors: Record<string, string>;
  rooms: DashboardRoomItem[];
  floors: FloorData[];
  pendingHousekeepingTasks: number;
  completedToday: number;
  upcomingMaintenance: number;
  maintenanceCompliancePct: number;
  totalMaintenanceCompleted: number;
  pendingCharges: number;
}

@Injectable({ providedIn: 'root' })
export class HousekeepingApiService {
  private readonly http = inject(HttpClient);

  // ── Room Status ──

  getRoomStatus(propId?: number, status?: string, page = 1) {
    let params = new HttpParams().set('page', String(page));
    if (propId) params = params.set('prop_id', String(propId));
    if (status) params = params.set('status', status);
    return this.http.get<PaginatedResponse<RoomStatusItem>>('/housekeeping/room-status', { params });
  }

  upsertRoomStatus(payload: { prop_id: number; room_type_id: string; room_label: string; status: string; note?: string }) {
    return this.http.put<RoomStatusItem>('/housekeeping/room-status', payload);
  }

  bulkUpdateRoomStatus(propId: number, roomLabels: string[], status: string, note = '') {
    return this.http.post<{ ok: boolean; updated_count: number }>(
      '/housekeeping/room-status/bulk',
      { prop_id: propId, room_labels: roomLabels, status, note },
    );
  }

  // ── Housekeeping Tasks ──

  getTasks(propId?: number, status?: string, assignedTo?: string, priority?: string, page = 1) {
    let params = new HttpParams().set('page', String(page));
    if (propId) params = params.set('prop_id', String(propId));
    if (status) params = params.set('status', status);
    if (assignedTo) params = params.set('assigned_to', assignedTo);
    if (priority) params = params.set('priority', priority);
    return this.http.get<PaginatedResponse<HousekeepingTaskItem>>('/housekeeping/tasks', { params });
  }

  createTask(payload: { prop_id: number; room_id: string; task_type: string; assigned_to?: string; priority?: string; note?: string; scheduled_date?: string }) {
    return this.http.post<HousekeepingTaskItem>('/housekeeping/tasks', payload);
  }

  updateTask(taskId: string, payload: { prop_id: number; room_id: string; task_type: string; assigned_to?: string; priority?: string; note?: string; scheduled_date?: string; status?: string }) {
    return this.http.put<HousekeepingTaskItem>(`/housekeeping/tasks/${taskId}`, payload);
  }

  deleteTask(taskId: string) {
    return this.http.delete<HousekeepingTaskItem>(`/housekeeping/tasks/${taskId}`);
  }

  completeTask(taskId: string, note = '') {
    return this.http.post<HousekeepingTaskItem>(`/housekeeping/tasks/${taskId}/complete`, { note });
  }

  // ── Maintenance ──

  getMaintenance(propId?: number, status?: string, priority?: string, page = 1) {
    let params = new HttpParams().set('page', String(page));
    if (propId) params = params.set('prop_id', String(propId));
    if (status) params = params.set('status', status);
    if (priority) params = params.set('priority', priority);
    return this.http.get<PaginatedResponse<MaintenanceTaskItem>>('/housekeeping/maintenance', { params });
  }

  createMaintenance(payload: { prop_id: number; room_id: string; task_type: string; title: string; description?: string; priority?: string; scheduled_date?: string; auto_block?: boolean; status?: string }) {
    return this.http.post<MaintenanceTaskItem>('/housekeeping/maintenance', payload);
  }

  updateMaintenance(taskId: string, payload: { prop_id: number; room_id: string; task_type: string; title: string; description?: string; priority?: string; scheduled_date?: string; auto_block?: boolean; status?: string }) {
    return this.http.put<MaintenanceTaskItem>(`/housekeeping/maintenance/${taskId}`, payload);
  }

  completeMaintenance(taskId: string, note = '') {
    return this.http.post<MaintenanceTaskItem>(`/housekeeping/maintenance/${taskId}/complete`, { note });
  }

  deleteMaintenance(taskId: string) {
    return this.http.delete<MaintenanceTaskItem>(`/housekeeping/maintenance/${taskId}`);
  }

  // ── Additional Charges ──

  getCharges(bookingId?: string, propId?: number, page = 1) {
    let params = new HttpParams().set('page', String(page));
    if (bookingId) params = params.set('booking_id', bookingId);
    if (propId) params = params.set('prop_id', String(propId));
    return this.http.get<PaginatedResponse<AdditionalChargeItem>>('/housekeeping/charges', { params });
  }

  createCharge(payload: { booking_id: string; prop_id: number; concept: string; amount: number; quantity?: number; note?: string; charge_date?: string }) {
    return this.http.post<AdditionalChargeItem>('/housekeeping/charges', payload);
  }

  updateCharge(chargeId: string, payload: { concept?: string; amount?: number; quantity?: number; note?: string; charge_date?: string }) {
    return this.http.put<AdditionalChargeItem>(`/housekeeping/charges/${chargeId}`, payload);
  }

  deleteCharge(chargeId: string) {
    return this.http.delete<{ ok: boolean; deleted_id: string; booking_id: string }>(`/housekeeping/charges/${chargeId}`);
  }

  // ── Cleaning Actions ──

  startCleaning(propId: number, roomLabel: string, assignedTo: string) {
    return this.http.post<{ ok: boolean; room_label: string; new_status: string }>(
      '/housekeeping/cleaning/start',
      { prop_id: propId, room_label: roomLabel, assigned_to: assignedTo },
    );
  }

  completeCleaning(payload: {
    prop_id: number;
    room_label: string;
    assigned_to?: string;
    observations?: string;
    damage_found?: boolean;
    damage_description?: string;
    lost_object_found?: boolean;
    lost_object_description?: string;
    needs_maintenance?: boolean;
    maintenance_description?: string;
  }) {
    return this.http.post<{ ok: boolean; room_label: string; new_status: string; maintenance_created?: boolean; maintenance_task_id?: string }>(
      '/housekeeping/cleaning/complete',
      payload,
    );
  }

  approveCleaning(propId: number, roomLabel: string, inspectedBy: string, note = '', setOccupied = false) {
    return this.http.post<{ ok: boolean; room_label: string; new_status: string }>(
      '/housekeeping/cleaning/approve',
      { prop_id: propId, room_label: roomLabel, inspected_by: inspectedBy, note, set_occupied: setOccupied },
    );
  }

  // ── Dashboard ──

  getDashboard(propId?: number) {
    const params = propId ? new HttpParams().set('prop_id', String(propId)) : undefined;
    return this.http.get<HousekeepingDashboard>('/housekeeping/dashboard', { params });
  }

  getUpcomingEvents(propId?: number) {
    let params = new HttpParams();
    if (propId) params = params.set('prop_id', String(propId));
    return this.http.get<{ id: string; event_type: string; room_label: string; title?: string; task_type: string; status: string; priority: string; scheduled_date?: string; created_at: string; assigned_to?: string; note?: string }[]>(
      '/housekeeping/upcoming-events', { params }
    );
  }

  // ── Weekly Calendar ──

  getWeeklyCalendar(propId: number, weekStart: string, assignedTo?: string) {
    let params = new HttpParams()
      .set('prop_id', String(propId))
      .set('week_start', weekStart);
    if (assignedTo) params = params.set('assigned_to', assignedTo);
    return this.http.get<WeeklyCalendarData>('/housekeeping/calendar-week', { params });
  }

  // ── Room Status History / Audit ──

  getRoomStatusHistory(propId?: number, roomLabel?: string, bookingId?: string, page = 1) {
    let params = new HttpParams().set('page', String(page));
    if (propId) params = params.set('prop_id', String(propId));
    if (roomLabel) params = params.set('room_label', roomLabel);
    if (bookingId) params = params.set('booking_id', bookingId);
    return this.http.get<PaginatedResponse<RoomStatusHistoryEntry>>('/housekeeping/room-status/history', { params });
  }

  // ── Staff users ──

  getStaff(propId?: number) {
    const params = propId ? new HttpParams().set('prop_id', String(propId)) : undefined;
    return this.http.get<{ staff: StaffUser[] }>('/housekeeping/staff', { params });
  }

  syncRoomStatus(propId: number) {
    return this.http.post<{ synced: boolean; prop_id: number; created: number; total_rooms: number }>(
      '/housekeeping/room-status/sync',
      { prop_id: propId },
    );
  }
}
