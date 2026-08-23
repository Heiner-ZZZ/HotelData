import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import type { RoomStatusAnalytics } from '../models/room-status-analytics.model';
import type { RoomStatusAnalyticsDto } from '../models/room-status-analytics.dto';
import { mapRoomStatusAnalytics } from '../mappers/room-status-analytics.mapper';

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
  estimatedCost: number | null;
  actualCost: number | null;
  currency: string;
  vendorName: string | null;
  vendorId: string | null;
  expenseInvoiceId: string | null;
  ledgerJournalId: string | null;
  inventoryConsumptionIds: string[];
  ledgerStatus?: 'pending' | 'posted' | 'failed' | 'not_linked' | string;
  ledgerPostingStatus?: 'posted' | 'failed' | 'pending' | string | null;
  ledgerPostingError?: string | null;
  financialLinkStatus?: 'linked' | 'pending' | 'invalid_invoice' | 'invoice_not_found_or_foreign' | 'not_linked' | string;
  financialLinkError?: string | null;
  costStatus?: string | null;
  createdAt: string;
  completedAt: string | null;
}

/** Read-only operational item used by the reception Timeline overlay. */
export interface UpcomingHousekeepingEvent {
  id: string;
  event_type: 'maintenance' | 'task' | string;
  prop_id?: number;
  hotel_room_id?: string;
  room_id?: string;
  room_label?: string;
  title?: string;
  task_type?: string;
  status?: string;
  priority?: string;
  scheduled_date?: string;
  created_at?: string;
  assigned_to?: string;
  note?: string;
  description?: string;
}

/** Availability blackout returned by the existing partner read endpoint. */
export interface PropertyBlackoutItem {
  blackout_id: string;
  prop_id: number;
  room_type_id: string;
  start_date: string;
  end_date: string;
  reason: string;
  blocked_rooms: number;
  room_numbers?: string[];
  range_label?: string;
}

export interface PropertyBlackoutsResponse {
  items: PropertyBlackoutItem[];
  total: number;
}

export interface UpcomingEventsQueryResponse {
  items: UpcomingHousekeepingEvent[];
  total?: number;
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
  postingStatus?: 'pending' | 'posted' | 'posting_failed' | 'reversal_failed' | 'reversed' | string;
  postingError?: string | null;
  postingId?: string | null;
  postingReference?: string | null;
  postingReferenceType?: string | null;
  domainEventId?: string | null;
  domainEventStatus?: 'posted' | 'failed' | string;
  folioId?: string | null;
  folioNumber?: string | null;
  invoiceReconciliationStatus?: 'posted' | 'failed' | string;
  invoiceReconciliationError?: string | null;
  reversedAt?: string | null;
  status?: 'active' | 'reversed' | string;
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

export interface HousekeepingOperationsRow {
  date: string;
  prop_id: number;
  hotel_label: string;
  tasks_total: number;
  tasks_completed: number;
  tasks_completed_on_time: number;
  tasks_with_completed_at: number;
  maintenance_total: number;
  maintenance_completed: number;
  maintenance_completed_on_time: number;
  rooms_status_events: number;
  rooms_to_clean: number;
  rooms_cleaned: number;
  rooms_available_after_cleaning: number;
  avg_cleaning_minutes: number | null;
  avg_checkout_to_available_minutes: number | null;
  rotation_observed: number;
  inventory_available_rooms: number;
  inventory_blocked_rooms: number;
  inventory_total_rooms: number;
  charges_total: number;
  charges_amount: number;
  supplier_country_coverage: number;
}

export interface HousekeepingOperationsAnalytics {
  available: boolean;
  source: 'clickhouse' | string;
  date_from: string;
  date_to: string;
  prop_id: number | null;
  rows: HousekeepingOperationsRow[];
  summary: {
    tasks_total: number;
    tasks_completed: number;
    maintenance_total: number;
    maintenance_completed: number;
    rooms_cleaned: number;
    inventory_available_rooms: number;
    inventory_blocked_rooms: number;
    charges_amount: number;
    rotation_observed: number;
    avg_cleaning_minutes: number | null;
    avg_checkout_to_available_minutes: number | null;
  };
  message?: string;
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

  private _propParams(propId: number): HttpParams {
    return new HttpParams().set('prop_id', String(propId));
  }

  // ── Room Status ──

  getRoomStatus(propId?: number, status?: string, page = 1) {
    let params = new HttpParams().set('page', String(page));
    if (propId) params = params.set('prop_id', String(propId));
    if (status) params = params.set('status', status);
    return this.http.get<PaginatedResponse<RoomStatusItem>>('/housekeeping/room-status', { params });
  }

  upsertRoomStatus(payload: { prop_id: number; room_type_id: string; room_label: string; status: string; note?: string }) {
    return this.http.put<RoomStatusItem>('/housekeeping/room-status', payload, { params: this._propParams(payload.prop_id) });
  }

  bulkUpdateRoomStatus(propId: number, roomLabels: string[], status: string, note = '') {
    return this.http.post<{ ok: boolean; updated_count: number }>(
      '/housekeeping/room-status/bulk',
      { prop_id: propId, room_labels: roomLabels, status, note },
      { params: this._propParams(propId) },
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
    return this.http.post<HousekeepingTaskItem>('/housekeeping/tasks', payload, { params: this._propParams(payload.prop_id) });
  }

  updateTask(taskId: string, payload: { prop_id: number; room_id: string; task_type: string; assigned_to?: string; priority?: string; note?: string; scheduled_date?: string; status?: string }) {
    return this.http.put<HousekeepingTaskItem>(`/housekeeping/tasks/${taskId}`, payload, { params: this._propParams(payload.prop_id) });
  }

  deleteTask(taskId: string, propId: number) {
    return this.http.delete<HousekeepingTaskItem>(`/housekeeping/tasks/${taskId}`, { params: this._propParams(propId) });
  }

  completeTask(taskId: string, propId: number, note = '') {
    return this.http.post<HousekeepingTaskItem>(`/housekeeping/tasks/${taskId}/complete`, { note }, { params: this._propParams(propId) });
  }

  // ── Maintenance ──

  getMaintenance(propId?: number, status?: string, priority?: string, page = 1) {
    let params = new HttpParams().set('page', String(page));
    if (propId) params = params.set('prop_id', String(propId));
    if (status) params = params.set('status', status);
    if (priority) params = params.set('priority', priority);
    return this.http.get<PaginatedResponse<MaintenanceTaskItem>>('/housekeeping/maintenance', { params });
  }

  createMaintenance(payload: { prop_id: number; room_id: string; task_type: string; title: string; description?: string; priority?: string; scheduled_date?: string; auto_block?: boolean; status?: string; estimated_cost?: number; actual_cost?: number; currency?: string; vendor_name?: string; vendor_id?: string; expense_invoice_id?: string; ledger_journal_id?: string; inventory_consumption_ids?: string[] }) {
    return this.http.post<MaintenanceTaskItem>('/housekeeping/maintenance', payload, { params: this._propParams(payload.prop_id) });
  }

  updateMaintenance(taskId: string, payload: { prop_id: number; room_id: string; task_type: string; title: string; description?: string; priority?: string; scheduled_date?: string; auto_block?: boolean; status?: string; estimated_cost?: number; actual_cost?: number; currency?: string; vendor_name?: string; vendor_id?: string; expense_invoice_id?: string; ledger_journal_id?: string; inventory_consumption_ids?: string[] }) {
    return this.http.put<MaintenanceTaskItem>(`/housekeeping/maintenance/${taskId}`, payload, { params: this._propParams(payload.prop_id) });
  }

  completeMaintenance(taskId: string, propId: number, note = '') {
    return this.http.post<MaintenanceTaskItem>(`/housekeeping/maintenance/${taskId}/complete`, { note }, { params: this._propParams(propId) });
  }

  reconcileNoCostMaintenance(taskId: string, propId: number) {
    return this.http.post<MaintenanceTaskItem>(`/housekeeping/maintenance/${taskId}/reconcile-no-cost`, {}, { params: this._propParams(propId) });
  }

  deleteMaintenance(taskId: string, propId: number) {
    return this.http.delete<MaintenanceTaskItem>(`/housekeeping/maintenance/${taskId}`, { params: this._propParams(propId) });
  }

  recoverCharge(chargeId: string, propId: number) {
    return this.http.post<AdditionalChargeItem>(`/housekeeping/charges/${chargeId}/recover`, {}, { params: this._propParams(propId) });
  }

  // ── Additional Charges ──

  getCharges(bookingId?: string, propId?: number, page = 1) {
    let params = new HttpParams().set('page', String(page));
    if (bookingId) params = params.set('booking_id', bookingId);
    if (propId) params = params.set('prop_id', String(propId));
    return this.http.get<PaginatedResponse<AdditionalChargeItem>>('/housekeeping/charges', { params });
  }

  createCharge(payload: { booking_id: string; prop_id: number; concept: string; amount: number; quantity?: number; note?: string; charge_date?: string }) {
    return this.http.post<AdditionalChargeItem>('/housekeeping/charges', payload, { params: this._propParams(payload.prop_id) });
  }

  updateCharge(chargeId: string, payload: { concept?: string; amount?: number; quantity?: number; note?: string; charge_date?: string }, propId: number) {
    return this.http.put<AdditionalChargeItem>(`/housekeeping/charges/${chargeId}`, payload, { params: this._propParams(propId) });
  }

  repairChargePosting(chargeId: string, propId: number) {
    return this.http.post<AdditionalChargeItem>(
      `/housekeeping/charges/${chargeId}/repair-posting`,
      {},
      { params: this._propParams(propId), withCredentials: true },
    );
  }

  deleteCharge(chargeId: string, propId: number) {
    return this.http.delete<{ ok: boolean; deleted_id: string; booking_id: string }>(`/housekeeping/charges/${chargeId}`, { params: this._propParams(propId) });
  }

  // ── Cleaning Actions ──

  startCleaning(propId: number, roomLabel: string, assignedTo: string) {
    return this.http.post<{ ok: boolean; room_label: string; new_status: string }>(
      '/housekeeping/cleaning/start',
      { prop_id: propId, room_label: roomLabel, assigned_to: assignedTo },
      { params: this._propParams(propId) },
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
      { params: this._propParams(payload.prop_id) },
    );
  }

  approveCleaning(propId: number, roomLabel: string, inspectedBy: string, note = '', setOccupied = false) {
    return this.http.post<{ ok: boolean; room_label: string; new_status: string }>(
      '/housekeeping/cleaning/approve',
      { prop_id: propId, room_label: roomLabel, inspected_by: inspectedBy, note, set_occupied: setOccupied },
      { params: this._propParams(propId) },
    );
  }

  // ── Dashboard ──

  getOperationsAnalytics(propId?: number, dateFrom?: string, dateTo?: string, days = 30) {
    let params = new HttpParams().set('days', String(days));
    if (propId) params = params.set('prop_id', String(propId));
    if (dateFrom) params = params.set('date_from', dateFrom);
    if (dateTo) params = params.set('date_to', dateTo);
    return this.http.get<HousekeepingOperationsAnalytics>('/housekeeping/operations/analytics', { params });
  }

  getDashboard(propId?: number) {
    const params = propId ? new HttpParams().set('prop_id', String(propId)) : undefined;
    return this.http.get<HousekeepingDashboard>('/housekeeping/dashboard', { params });
  }

  getUpcomingEvents(propId?: number, days = 90) {
    let params = new HttpParams().set('days', String(days));
    if (propId) params = params.set('prop_id', String(propId));
    return this.http.get<UpcomingHousekeepingEvent[]>('/housekeeping/upcoming-events', { params });
  }

  getPropertyBlackouts(propId: number) {
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.get<PropertyBlackoutsResponse>('/management/availability/blackouts', { params });
  }

  // ── Weekly Calendar ──

  getWeeklyCalendar(propId: number, weekStart: string, assignedTo?: string) {
    let params = new HttpParams()
      .set('prop_id', String(propId))
      .set('week_start', weekStart);
    if (assignedTo) params = params.set('assigned_to', assignedTo);
    return this.http.get<WeeklyCalendarData>('/housekeeping/calendar-week', { params });
  }

  /** Simple O1.2 dashboard: matriz de estado de habitaciones (Mongo). */
  getRoomStatusAnalytics(propId?: number, status?: string, page = 1) {
    let params = new HttpParams().set('page', String(page));
    if (propId) params = params.set('prop_id', String(propId));
    if (status) params = params.set('status', status);
    return this.http
      .get<RoomStatusAnalyticsDto>('/housekeeping/room-status/analytics', { params })
      .pipe(map((dto) => mapRoomStatusAnalytics(dto)));
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
    // El backend exige prop_id por QUERY (gate por-hotel + consistencia
    // query↔body); solo el body daba 400 (mismo contrato que openShift).
    const params = new HttpParams().set('prop_id', String(propId));
    return this.http.post<{ synced: boolean; prop_id: number; created: number; total_rooms: number }>(
      '/housekeeping/room-status/sync',
      { prop_id: propId },
      { params },
    );
  }
}
