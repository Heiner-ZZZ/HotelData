/** View models tipados de la cola de conciliación + mappers wire → model. */
import type {
  AdminPaymentDto,
  AdminPaymentListDto,
  PublicPricingPlanDto,
} from './reconciliation.dto';

export type AdminPaymentStatus = 'pending_verification' | 'verified' | 'rejected';

export interface AdminPayment {
  id: string;
  propId: number;
  hotelName: string;
  ownerUsername: string;
  method: string;
  reference: string;
  amount: number;
  status: AdminPaymentStatus;
  createdAt: string | null;
}

export interface AdminPaymentQueue {
  items: AdminPayment[];
  total: number;
  page: number;
  pageSize: number;
}

export interface PricingBandOption {
  band: number;
  label: string;
  monthlyUsd: number;
}

export function mapAdminPayment(dto: AdminPaymentDto): AdminPayment {
  return {
    id: dto.id,
    propId: dto.prop_id,
    hotelName: dto.hotel_name ?? '',
    ownerUsername: dto.owner_username ?? '',
    method: dto.method,
    reference: dto.reference ?? '',
    amount: dto.amount,
    status: dto.status,
    createdAt: dto.created_at ?? null,
  };
}

export function mapAdminPaymentQueue(dto: AdminPaymentListDto): AdminPaymentQueue {
  return {
    items: (dto.items ?? []).map(mapAdminPayment),
    total: dto.total ?? 0,
    page: dto.page ?? 1,
    pageSize: dto.page_size ?? 20,
  };
}

export function mapPricingBand(dto: PublicPricingPlanDto): PricingBandOption {
  return {
    band: dto.band,
    label: dto.label,
    monthlyUsd: dto.monthly_usd,
  };
}
