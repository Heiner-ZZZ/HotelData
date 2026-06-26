import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { map, Observable } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import type { EarningsSummaryDto, EarningsListDto, EarningsItemDto } from '../models/earnings.dto';
import type { EarningsSummary, EarningsList, EarningsItem } from '../models/earnings.model';

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
}
