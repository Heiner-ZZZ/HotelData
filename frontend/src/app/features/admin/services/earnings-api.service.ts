import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { map, Observable } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import type { EarningsSummaryDto, EarningsListDto, EarningsItemDto, WeeklyEarningPointDto } from '../models/earnings.dto';
import type { EarningsSummary, EarningsList, EarningsItem, WeeklyEarningPoint } from '../models/earnings.model';

function mapSummary(dto: EarningsSummaryDto): EarningsSummary {
  return {
    totalCommission: dto.total_commission,
    totalBookings: dto.total_bookings,
    avgCommission: dto.avg_commission,
    pendingCount: dto.pending_count,
    paidCount: dto.paid_count,
  };
}

function mapItem(dto: EarningsItemDto): EarningsItem {
  return {
    bookingId: dto.booking_id,
    propId: dto.prop_id,
    hotelName: dto.hotel_name,
    commissionPct: dto.commission_pct,
    bookingTotal: dto.booking_total,
    commissionAmount: dto.commission_amount,
    status: dto.status,
    createdAt: dto.created_at,
  };
}

function mapList(dto: EarningsListDto): EarningsList {
  return {
    items: dto.items.map(mapItem),
    total: dto.total,
    page: dto.page,
    pageSize: dto.page_size,
    totalPages: dto.total_pages,
  };
}

@Injectable({ providedIn: 'root' })
export class EarningsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly base = `${this.apiConfig.baseUrl}/management/products/earnings`;

  getSummary(): Observable<EarningsSummary> {
    return this.http
      .get<EarningsSummaryDto>(`${this.base}/summary`, { withCredentials: true })
      .pipe(map(mapSummary));
  }

  list(page = 1, pageSize = 20): Observable<EarningsList> {
    const params = new HttpParams()
      .set('page', String(page))
      .set('page_size', String(pageSize));
    return this.http
      .get<EarningsListDto>(`${this.base}`, { params, withCredentials: true })
      .pipe(map(mapList));
  }

  markPaid(bookingId: string): Observable<EarningsItem | null> {
    return this.http
      .put<EarningsItemDto | null>(
        `${this.base}/${bookingId}/pay`,
        {},
        { withCredentials: true },
      )
      .pipe(map((dto) => (dto ? mapItem(dto) : null)));
  }

  getWeeklyEarnings(
    weeks = 12,
    startDate?: string,
    endDate?: string,
  ): Observable<WeeklyEarningPoint[]> {
    let params = new HttpParams().set('weeks', String(weeks));
    if (startDate) params = params.set('start_date', startDate);
    if (endDate) params = params.set('end_date', endDate);
    return this.http
      .get<{ items: WeeklyEarningPointDto[] }>(`${this.base}/weekly`, {
        params,
        withCredentials: true,
      })
      .pipe(
        map((res) =>
          res.items.map((dto) => ({
            label: dto.label,
            totalCommission: dto.total_commission,
            totalBookings: dto.total_bookings,
            paidCount: dto.paid_count,
            pendingCount: dto.pending_count,
          })),
        ),
      );
  }
}
