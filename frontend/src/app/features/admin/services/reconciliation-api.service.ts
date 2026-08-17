import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import type {
  AdminCancelRequestDto,
  AdminCancelResponseDto,
  AdminOverrideRequestDto,
  AdminOverrideResponseDto,
  AdminRejectRequestDto,
  AdminRejectResponseDto,
  AdminVerifyResponseDto,
} from '../models/reconciliation.dto';

/** Mutaciones de la cola de conciliación (Fase 4 — PLAN §6.2).\n *  Los GETs (cola de comprobantes) se hacen con ``httpResource`` en el\n *  componente; aquí viven solo los POSTs con ``HttpClient``. */
@Injectable({ providedIn: 'root' })
export class ReconciliationApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  private get base(): string {
    return `${this.apiConfig.baseUrl}/admin/subscriptions`;
  }

  /** Marca el comprobante como verificado (factura paid + suscripción active). */
  verify(paymentId: string): Observable<AdminVerifyResponseDto> {
    return this.http.post<AdminVerifyResponseDto>(
      `${this.base}/payments/${paymentId}/verify`,
      {},
      { withCredentials: true },
    );
  }

  /** Rechaza el comprobante con motivo obligatorio. */
  reject(paymentId: string, reason: string): Observable<AdminRejectResponseDto> {
    return this.http.post<AdminRejectResponseDto>(
      `${this.base}/payments/${paymentId}/reject`,
      { reason } satisfies AdminRejectRequestDto,
      { withCredentials: true },
    );
  }

  /** Override de precio negociado sobre la suscripción de un hotel. */
  override(
    propId: number,
    payload: AdminOverrideRequestDto,
  ): Observable<AdminOverrideResponseDto> {
    return this.http.post<AdminOverrideResponseDto>(
      `${this.base}/${propId}/override`,
      payload,
      { withCredentials: true },
    );
  }

  /** Cancela la suscripción de un hotel (terminal). */
  cancel(propId: number, reason: string): Observable<AdminCancelResponseDto> {
    return this.http.post<AdminCancelResponseDto>(
      `${this.base}/${propId}/cancel`,
      { reason } satisfies AdminCancelRequestDto,
      { withCredentials: true },
    );
  }
}
