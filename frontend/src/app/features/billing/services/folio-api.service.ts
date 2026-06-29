import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { map, Observable } from 'rxjs';

export interface FolioPosting {
  postingId: string;
  type: 'room' | 'charge' | 'discount' | 'payment' | 'adjustment';
  category: string;
  concept: string;
  amount: number;
  quantity: number;
  unitPrice: number;
  referenceId: string;
  referenceType: string;
  postedAt: string;
}

export interface FolioDto {
  id: string;
  folio_number: string;
  booking_id: string;
  prop_id: number;
  guest_name: string;
  guest_email: string;
  room_label: string;
  hotel_label: string;
  check_in_date: string;
  check_out_date: string;
  status: 'open' | 'closed';
  total_room: number;
  total_charges: number;
  total_discounts: number;
  total_payments: number;
  total_due: number;
  postings: FolioPostingRaw[];
  posting_count: number;
  created_at: string;
  closed_at: string | null;
  closed_by: string | null;
  invoice_id: string | null;
}

export interface FolioPostingRaw {
  posting_id: string;
  type: string;
  category: string;
  concept: string;
  amount: number;
  quantity: number;
  unit_price: number;
  reference_id: string;
  reference_type: string;
  posted_at: string;
}

export interface FolioViewModel {
  id: string;
  folioNumber: string;
  bookingId: string;
  propId: number;
  guestName: string;
  guestEmail: string;
  roomLabel: string;
  hotelLabel: string;
  checkInDate: string;
  checkOutDate: string;
  status: 'open' | 'closed';
  totalRoom: number;
  totalCharges: number;
  totalDiscounts: number;
  totalPayments: number;
  totalDue: number;
  postings: FolioPosting[];
  postingCount: number;
  createdAt: string;
  closedAt: string | null;
  closedBy: string | null;
  invoiceId: string | null;
}

export interface FolioPostPayload {
  posting_type: 'charge' | 'discount' | 'payment' | 'adjustment';
  category: string;
  concept: string;
  amount: number;
  quantity?: number;
  reference_id?: string;
  reference_type?: string;
}

export interface FolioClosePayload {
  invoice_id?: string;
}

export interface FolioCategory {
  id: string;
  label: string;
  icon: string;
}

function mapFolio(dto: FolioDto): FolioViewModel {
  return {
    id: dto.id,
    folioNumber: dto.folio_number,
    bookingId: dto.booking_id,
    propId: dto.prop_id,
    guestName: dto.guest_name,
    guestEmail: dto.guest_email,
    roomLabel: dto.room_label,
    hotelLabel: dto.hotel_label,
    checkInDate: dto.check_in_date,
    checkOutDate: dto.check_out_date,
    status: dto.status,
    totalRoom: dto.total_room,
    totalCharges: dto.total_charges,
    totalDiscounts: dto.total_discounts,
    totalPayments: dto.total_payments,
    totalDue: dto.total_due,
    postings: (dto.postings || []).map((p: FolioPostingRaw) => ({
      postingId: p.posting_id,
      type: p.type as FolioPosting['type'],
      category: p.category,
      concept: p.concept,
      amount: p.amount,
      quantity: p.quantity,
      unitPrice: p.unit_price,
      referenceId: p.reference_id,
      referenceType: p.reference_type,
      postedAt: p.posted_at,
    })),
    postingCount: dto.posting_count,
    createdAt: dto.created_at,
    closedAt: dto.closed_at,
    closedBy: dto.closed_by,
    invoiceId: dto.invoice_id,
  };
}

@Injectable({ providedIn: 'root' })
export class FolioApiService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/billing/folios';

  /** Get the folio for a booking. */
  getFolio(bookingId: string): Observable<FolioViewModel> {
    return this.http.get<FolioDto>(`${this.base}/${bookingId}`).pipe(map(mapFolio));
  }

  /** Post a transaction to the guest's folio. */
  postToFolio(bookingId: string, payload: FolioPostPayload): Observable<FolioViewModel> {
    return this.http.post<FolioDto>(`${this.base}/${bookingId}/post`, payload).pipe(map(mapFolio));
  }

  /** Close a folio at check-out. */
  closeFolio(bookingId: string, payload: FolioClosePayload = {}): Observable<FolioViewModel> {
    return this.http.post<FolioDto>(`${this.base}/${bookingId}/close`, payload).pipe(map(mapFolio));
  }

  /** List folios with optional filters. */
  listFolios(params?: { prop_id?: number; status?: string; page?: number; page_size?: number }): Observable<{ items: FolioDto[]; total: number; page: number; page_size: number; total_pages: number; has_next: boolean; has_prev: boolean }> {
    return this.http.get<{ items: FolioDto[]; total: number; page: number; page_size: number; total_pages: number; has_next: boolean; has_prev: boolean }>(`${this.base}`, { params: params as any });
  }

  /** Get available folio categories. */
  getCategories(): Observable<FolioCategory[]> {
    return this.http.get<FolioCategory[]>(`${this.base}/categories`);
  }
}
