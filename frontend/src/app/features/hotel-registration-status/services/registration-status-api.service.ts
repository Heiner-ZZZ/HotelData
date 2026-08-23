import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import type {
  EditPropertyPayloadDto,
  PatchPropertyResponseDto,
  PaymentMethodDto,
  RegistrationStatusDto,
  SuggestedBandDto,
} from '../models/registration-status.dto';
import type {
  PaymentMethod,
  RegistrationProperty,
  RegistrationStatus,
  SuggestedBand,
  TimelineEvent,
} from '../models/registration-status.model';

function mapSuggestedBand(dto: SuggestedBandDto | null | undefined): SuggestedBand | null {
  if (!dto) return null;
  return {
    band: dto.band,
    label: dto.label,
    monthlyUsd: dto.monthly_usd,
    annualMonthlyUsd: dto.annual_monthly_usd,
    minRooms: dto.min_rooms,
    maxRooms: dto.max_rooms,
  };
}

function mapProperty(dto: RegistrationStatusDto['property']): RegistrationProperty {
  return {
    name: dto.name,
    type: dto.type,
    city: dto.city,
    country: dto.country,
    totalRooms: dto.total_rooms,
    currency: dto.currency,
    contactPhone: dto.contact_phone,
    address: dto.address ?? '',
    latitude: dto.latitude ?? null,
    longitude: dto.longitude ?? null,
  };
}

function mapTimeline(events: RegistrationStatusDto['timeline']): TimelineEvent[] {
  return (events ?? []).map((e) => ({
    event: e.event,
    at: e.at ?? null,
    detail: e.detail ?? '',
  }));
}

function mapPaymentMethods(methods: PaymentMethodDto[] | undefined): PaymentMethod[] {
  return (methods ?? []).map((m) => ({
    code: m.code,
    label: m.label,
    sortOrder: m.sort_order,
    details: m.details ?? {},
  }));
}

/** Mapeo wire → model. Exportado para que el componente lo use como `parse`
 *  del httpResource de la pantalla (convención: GET vía httpResource). */
export function mapRegistrationStatus(dto: RegistrationStatusDto): RegistrationStatus {
  return {
    approvalStatus: dto.approval_status,
    rejectedReason: dto.rejected_reason ?? null,
    feedback: dto.feedback ?? null,
    submittedAt: dto.submitted_at ?? null,
    statusChangedAt: dto.status_changed_at ?? null,
    property: mapProperty(dto.property),
    suggestedBand: mapSuggestedBand(dto.suggested_band),
    initialGraceDays: dto.initial_grace_days ?? 7,
    paymentMethods: mapPaymentMethods(dto.payment_methods),
    timeline: mapTimeline(dto.timeline),
  };
}

@Injectable({ providedIn: 'root' })
export class RegistrationStatusApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  /** PATCH /api/auth/register-property/me — edición de datos declarados. */
  editProperty(payload: EditPropertyPayloadDto): Observable<PatchPropertyResponseDto> {
    return this.http.patch<PatchPropertyResponseDto>(
      `${this.apiConfig.baseUrl}/auth/register-property/me`,
      payload,
      { withCredentials: true },
    );
  }
}
