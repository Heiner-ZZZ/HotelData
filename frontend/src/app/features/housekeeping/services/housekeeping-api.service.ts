import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';

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
  roomLabel: string;
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
  roomLabel: string;
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
}

export interface HousekeepingDashboard {
  totalRooms: number;
  occupied: number;
  occupancyRate: number;
  roomStatuses: Record<string, number>;
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
  private readonly apiConfig = inject(API_CONFIG);

  private get baseUrl() {
    return `${this.apiConfig.baseUrl}/housekeeping`;
  }

  // ── Room Status ──

  getRoomStatus(propId?: number, status?: string, page = 1) {
    let params = new HttpParams().set('page', String(page));
    if (propId) params = params.set('prop_id', String(propId));
    if (status) params = params.set('status', status);
    return this.http.get<PaginatedResponse<RoomStatusItem>>(`${this.baseUrl}/room-status`, { params, withCredentials: true });
  }

  upsertRoomStatus(payload: { prop_id: number; room_type_id: string; room_label: string; status: string; note?: string }) {
    return this.http.put<RoomStatusItem>(`${this.baseUrl}/room-status`, payload, { withCredentials: true });
  }

  bulkUpdateRoomStatus(propId: number, roomLabels: string[], status: string, note = '') {
    return this.http.post<{ ok: boolean; updated_count: number }>(
      `${this.baseUrl}/room-status/bulk`,
      { prop_id: propId, room_labels: roomLabels, status, note },
      { withCredentials: true }
    );
  }

  // ── Housekeeping Tasks ──

  getTasks(propId?: number, status?: string, assignedTo?: string, page = 1) {
    let params = new HttpParams().set('page', String(page));
    if (propId) params = params.set('prop_id', String(propId));
    if (status) params = params.set('status', status);
    if (assignedTo) params = params.set('assigned_to', assignedTo);
    return this.http.get<PaginatedResponse<HousekeepingTaskItem>>(`${this.baseUrl}/tasks`, { params, withCredentials: true });
  }

  createTask(payload: { prop_id: number; room_label: string; task_type: string; assigned_to?: string; priority?: string; note?: string; scheduled_date?: string }) {
    return this.http.post<HousekeepingTaskItem>(`${this.baseUrl}/tasks`, payload, { withCredentials: true });
  }

  updateTask(taskId: string, payload: { prop_id: number; room_label: string; task_type: string; assigned_to?: string; priority?: string; note?: string; scheduled_date?: string; status?: string }) {
    return this.http.put<HousekeepingTaskItem>(`${this.baseUrl}/tasks/${taskId}`, payload, { withCredentials: true });
  }

  deleteTask(taskId: string) {
    return this.http.delete<HousekeepingTaskItem>(`${this.baseUrl}/tasks/${taskId}`, { withCredentials: true });
  }

  completeTask(taskId: string, note = '') {
    return this.http.post<HousekeepingTaskItem>(`${this.baseUrl}/tasks/${taskId}/complete`, { note }, { withCredentials: true });
  }

  // ── Maintenance ──

  getMaintenance(propId?: number, status?: string, page = 1) {
    let params = new HttpParams().set('page', String(page));
    if (propId) params = params.set('prop_id', String(propId));
    if (status) params = params.set('status', status);
    return this.http.get<PaginatedResponse<MaintenanceTaskItem>>(`${this.baseUrl}/maintenance`, { params, withCredentials: true });
  }

  createMaintenance(payload: { prop_id: number; room_label: string; task_type: string; title: string; description?: string; priority?: string; scheduled_date?: string; auto_block?: boolean }) {
    return this.http.post<MaintenanceTaskItem>(`${this.baseUrl}/maintenance`, payload, { withCredentials: true });
  }

  updateMaintenance(taskId: string, payload: { prop_id: number; room_label: string; task_type: string; title: string; description?: string; priority?: string; scheduled_date?: string; auto_block?: boolean; status?: string }) {
    return this.http.put<MaintenanceTaskItem>(`${this.baseUrl}/maintenance/${taskId}`, payload, { withCredentials: true });
  }

  completeMaintenance(taskId: string, note = '') {
    return this.http.post<MaintenanceTaskItem>(`${this.baseUrl}/maintenance/${taskId}/complete`, { note }, { withCredentials: true });
  }

  deleteMaintenance(taskId: string) {
    return this.http.delete<MaintenanceTaskItem>(`${this.baseUrl}/maintenance/${taskId}`, { withCredentials: true });
  }

  // ── Additional Charges ──

  getCharges(bookingId?: string, propId?: number, page = 1) {
    let params = new HttpParams().set('page', String(page));
    if (bookingId) params = params.set('booking_id', bookingId);
    if (propId) params = params.set('prop_id', String(propId));
    return this.http.get<PaginatedResponse<AdditionalChargeItem>>(`${this.baseUrl}/charges`, { params, withCredentials: true });
  }

  createCharge(payload: { booking_id: string; prop_id: number; concept: string; amount: number; quantity?: number; note?: string }) {
    return this.http.post<AdditionalChargeItem>(`${this.baseUrl}/charges`, payload, { withCredentials: true });
  }

  // ── Dashboard ──

  getDashboard(propId?: number) {
    const params = propId ? new HttpParams().set('prop_id', String(propId)) : undefined;
    return this.http.get<HousekeepingDashboard>(`${this.baseUrl}/dashboard`, { params, withCredentials: true });
  }

  getUpcomingEvents(propId?: number) {
    let params = new HttpParams();
    if (propId) params = params.set('prop_id', String(propId));
    return this.http.get<Array<{ id: string; event_type: string; room_label: string; title?: string; task_type: string; status: string; priority: string; scheduled_date?: string; created_at: string; assigned_to?: string; note?: string }>>(
      `${this.baseUrl}/upcoming-events`, { params, withCredentials: true }
    );
  }

  // ── Room Status History / Audit ──

  getRoomStatusHistory(propId?: number, roomLabel?: string, bookingId?: string, page = 1) {
    let params = new HttpParams().set('page', String(page));
    if (propId) params = params.set('prop_id', String(propId));
    if (roomLabel) params = params.set('room_label', roomLabel);
    if (bookingId) params = params.set('booking_id', bookingId);
    return this.http.get<PaginatedResponse<RoomStatusHistoryEntry>>(`${this.baseUrl}/room-status/history`, { params, withCredentials: true });
  }

  syncRoomStatus(propId: number) {
    return this.http.post<{ synced: boolean; prop_id: number; created: number; total_rooms: number }>(
      `${this.baseUrl}/room-status/sync`,
      { prop_id: propId },
      { withCredentials: true },
    );
  }
}
