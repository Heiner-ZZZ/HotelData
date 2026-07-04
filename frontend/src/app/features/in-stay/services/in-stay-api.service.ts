import { inject, Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { toSignal } from '@angular/core/rxjs-interop';
import { map, Observable } from 'rxjs';

import {
  ChatMessage,
  CompendiumInfo,
  Conversation,
  PortalData,
  ServiceRequest,
  StaySession,
} from '../models/in-stay.model';

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
    return this.http.post<StaySession>('/api/stay/my-session', { booking_id: bookingId });
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

  listRequests(propId?: number, status?: string): Observable<PaginatedResponse<ServiceRequest>> {
    const params: Record<string, string> = {};
    if (propId) params['prop_id'] = String(propId);
    if (status) params['status'] = status;
    return this.http.get<PaginatedResponse<ServiceRequest>>('/api/stay/requests', { params });
  }

  updateRequest(requestId: string, status: string, staffResponse: string = ''): Observable<{ ok: boolean }> {
    return this.http.put<{ ok: boolean }>(`/api/stay/requests/${requestId}`, { status, staff_response: staffResponse });
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
}
