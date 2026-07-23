import type { EarningsSummaryDto, EarningsListDto, EarningsItemDto } from '../models/earnings.dto';
import type { EarningsSummary, EarningsList, EarningsItem } from '../models/earnings.model';

export function mapSummary(dto: EarningsSummaryDto): EarningsSummary {
  return {
    totalCommission: dto.total_commission,
    totalBookings: dto.total_bookings,
    avgCommission: dto.avg_commission,
    pendingCount: dto.pending_count,
    paidCount: dto.paid_count,
  };
}

export function mapItem(dto: EarningsItemDto): EarningsItem {
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

export function mapList(dto: EarningsListDto): EarningsList {
  return {
    items: dto.items.map(mapItem),
    total: dto.total,
    page: dto.page,
    pageSize: dto.page_size,
    totalPages: dto.total_pages,
  };
}
