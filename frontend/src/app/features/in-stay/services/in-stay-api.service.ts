import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map } from 'rxjs';

import {
  ChatMessage,
  Conversation,
  PortalData,
  ServiceRequest,
  StaySession,
} from '../models/in-stay.model';
import type { ServiceRequestsAnalyticsDto } from '../models/service-requests-analytics.dto';
import type { ServiceRequestsAnalytics } from '../models/service-requests-analytics.model';

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

@Injectable({ providedIn: 'root' })
export class InStayApiService {
  private readonly http = inject(HttpClient);

  // ── Authenticated guest endpoint (JWT, no token needed) ──

  getMyStaySession(bookingId: string): Observable<StaySession> {
    return this.http.post<StaySession>('/api/stay/my-session', { booking_id: bookingId }, { withCredentials: true });
  }

  // ── Staff endpoints ──

  createSession(data: {
    booking_id: string;
    prop_id: number;
    room_label: string;
    guest_name: string;
    check_in: string;
    check_out: string;
  }): Observable<StaySession> {
    return this.http.post<StaySession>('/api/stay/sessions', data);
  }

  listSessions(propId?: number): Observable<{ items: StaySession[]; total: number }> {
    const params: Record<string, string> = {};
    if (propId) params['prop_id'] = String(propId);
    return this.http.get<{ items: StaySession[]; total: number }>('/api/stay/sessions', { params });
  }

  deactivateSession(token: string): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>(`/api/stay/sessions/${token}/deactivate`, {});
  }

  // ── Staff: Service Requests ──

  /** Simple I1.1 dashboard: solicitudes por estado y tipo (Mongo). */
  getRequestsAnalytics(params: {
    prop_id?: number;
    request_type?: string;
    status?: string;
    date_from?: string;
    date_to?: string;
    page?: number;
    page_size?: number;
  }): Observable<ServiceRequestsAnalytics> {
    const q: Record<string, string> = {};
    if (params.prop_id) q['prop_id'] = String(params.prop_id);
    if (params.request_type) q['request_type'] = params.request_type;
    if (params.status) q['status'] = params.status;
    if (params.date_from) q['date_from'] = params.date_from;
    if (params.date_to) q['date_to'] = params.date_to;
    if (params.page) q['page'] = String(params.page);
    if (params.page_size) q['page_size'] = String(params.page_size);
    return this.http.get<ServiceRequestsAnalyticsDto>('/api/stay/requests/analytics', { params: q }).pipe(
      map((dto) => ({
        available: dto.available,
        source: dto.source,
        propId: dto.prop_id,
        summary: {
          total: dto.summary?.total ?? 0,
          pending: dto.summary?.pending ?? 0,
          inProgress: dto.summary?.in_progress ?? 0,
          completed: dto.summary?.completed ?? 0,
          cancelled: dto.summary?.cancelled ?? 0,
          avgResolutionMinutes: dto.summary?.avg_resolution_minutes ?? null,
          resolvedCount: dto.summary?.resolved_count ?? 0,
        },
        series: {
          labels: dto.series?.labels ?? [],
          keys: dto.series?.keys ?? [],
          datasets: dto.series?.datasets ?? [],
          dailyLabels: dto.series?.daily_labels ?? [],
          dailyStatuses: dto.series?.daily_statuses ?? [],
        },
        rows: (dto.rows ?? []).map((r) => ({
          id: r._id,
          bookingId: r.booking_id,
          propId: r.prop_id,
          roomLabel: r.room_label,
          requestType: r.request_type,
          requestTypeLabel: r.request_type_label,
          description: r.description,
          status: r.status,
          statusLabel: r.status_label,
          createdAt: r.created_at,
          resolvedAt: r.resolved_at,
        })),
        total: dto.total ?? 0,
        page: dto.page ?? 1,
        pageSize: dto.page_size ?? 20,
        totalPages: dto.total_pages ?? 1,
        hasNext: dto.has_next ?? false,
        hasPrev: dto.has_prev ?? false,
      })),
    );
  }

  listRequests(propId?: number, status?: string): Observable<PaginatedResponse<ServiceRequest>> {
    const params: Record<string, string> = {};
    if (propId) params['prop_id'] = String(propId);
    if (status) params['status'] = status;
    return this.http.get<PaginatedResponse<ServiceRequest>>('/api/stay/requests', { params });
  }

  updateRequest(requestId: string, status: string, staffResponse = '', newCheckOutDate?: string): Observable<{ ok: boolean }> {
    const body: Record<string, string> = { status, staff_response: staffResponse };
    if (newCheckOutDate) body['new_check_out_date'] = newCheckOutDate;
    return this.http.put<{ ok: boolean }>(`/api/stay/requests/${requestId}`, body);
  }

  staffCreateRequest(bookingId: string, requestType: string, description = ''): Observable<{ ok: boolean; request_id: string }> {
    return this.http.post<{ ok: boolean; request_id: string }>('/api/stay/requests', {
      booking_id: bookingId,
      request_type: requestType,
      description,
    });
  }

  // ── Staff: Chat ──

  listConversations(propId?: number): Observable<{ conversations: Conversation[] }> {
    const params: Record<string, string> = {};
    if (propId) params['prop_id'] = String(propId);
    return this.http.get<{ conversations: Conversation[] }>('/api/stay/conversations', { params });
  }

  getConversationMessages(roomLabel: string, propId?: number): Observable<{ messages: ChatMessage[] }> {
    const params: Record<string, string> = {};
    if (propId) params['prop_id'] = String(propId);
    return this.http.get<{ messages: ChatMessage[] }>(`/api/stay/conversations/${roomLabel}`, { params });
  }

  staffReply(roomLabel: string, message: string): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>(`/api/stay/conversations/${roomLabel}/reply`, { message });
  }

  // ── Guest endpoints (token-based) ──

  getPortalData(token: string): Observable<PortalData> {
    return this.http.get<PortalData>('/api/stay/guest/portal', { params: { token } });
  }

  toggleDnd(token: string): Observable<{ ok: boolean; dnd_active: boolean; message: string }> {
    return this.http.post<{ ok: boolean; dnd_active: boolean; message: string }>('/api/stay/guest/dnd/toggle', { token });
  }

  getChatMessages(token: string): Observable<{ messages: ChatMessage[] }> {
    return this.http.get<{ messages: ChatMessage[] }>('/api/stay/guest/chat', { params: { token } });
  }

  sendMessage(token: string, message: string): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>('/api/stay/guest/chat', {
      token,
      message,
    });
  }

  getRequests(token: string): Observable<{ items: ServiceRequest[] }> {
    return this.http.get<{ items: ServiceRequest[] }>('/api/stay/guest/requests', { params: { token } });
  }

  createRequest(
    token: string,
    requestType: string,
    description: string
  ): Observable<{ ok: boolean; request_id: string }> {
    return this.http.post<{ ok: boolean; request_id: string }>('/api/stay/guest/requests', {
      token,
      request_type: requestType,
      description,
    });
  }

  // ── Lost & Found ──

  getLostItems(token: string): Observable<{ items: LostItem[] }> {
    return this.http.get<{ items: LostItem[] }>('/api/stay/guest/lost-items', { params: { token } });
  }

  // ── Staff: Lost & Found ──

  listLostFound(params?: { prop_id?: number; status?: string; search?: string; page?: number; page_size?: number }): Observable<PaginatedResponse<Record<string, unknown>>> {
    const q: Record<string, string> = {};
    if (params?.prop_id) q['prop_id'] = String(params.prop_id);
    if (params?.status) q['status'] = params.status;
    if (params?.search) q['search'] = params.search;
    if (params?.page) q['page'] = String(params.page);
    if (params?.page_size) q['page_size'] = String(params.page_size);
    return this.http.get<PaginatedResponse<Record<string, unknown>>>('/api/lost-and-found', { params: q });
  }

  createLostItem(data: { prop_id: number; item_name: string; description?: string; found_location?: string; found_by?: string; booking_id?: string; guest_name?: string }): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>('/api/lost-and-found', data);
  }

  claimLostItem(itemId: string, returnedTo = '', notes = ''): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`/api/lost-and-found/${itemId}/claim`, { returned_to: returnedTo, notes });
  }

  disposeLostItem(itemId: string, notes = ''): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(`/api/lost-and-found/${itemId}/dispose`, { notes });
  }

  cancelRequest(token: string, requestId: string): Observable<{ ok: boolean; message: string }> {
    return this.http.post<{ ok: boolean; message: string }>(`/api/stay/guest/requests/${requestId}/cancel`, { token });
  }
}

export interface LostItem {
  _id: string;
  description: string;
  status: string;
  location_found: string;
  reported_by: string;
  returned_to: string;
  created_at: string;
}
