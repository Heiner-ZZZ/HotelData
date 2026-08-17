import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import type {
  ChooseSubscriptionRequestDto,
  ChooseSubscriptionResponseDto,
  PaySubscriptionRequestDto,
  PaySubscriptionResponseDto,
} from '../models/subscription.dto';

/** Mutaciones de la suscripción del dueño (Fase 3 UI — PLAN_SUSCRIPCION_Y_PAGOS.md).\n *  Los GETs se hacen con ``httpResource`` en el componente (convención del\n *  proyecto); aquí viven solo los POSTs con ``HttpClient``. */
@Injectable({ providedIn: 'root' })
export class SubscriptionApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  private get base(): string {
    return `${this.apiConfig.baseUrl}/billing/subscriptions`;
  }

  /** Registra el comprobante de pago → ``pending_verification``. */
  pay(payload: PaySubscriptionRequestDto): Observable<PaySubscriptionResponseDto> {
    return this.http.post<PaySubscriptionResponseDto>(
      `${this.base}/me/pay`,
      payload,
      { withCredentials: true },
    );
  }

  /** Confirma ciclo + método de pago (banda derivada, no libre). */
  choose(payload: ChooseSubscriptionRequestDto): Observable<ChooseSubscriptionResponseDto> {
    return this.http.post<ChooseSubscriptionResponseDto>(
      `${this.base}/me/choose`,
      payload,
      { withCredentials: true },
    );
  }
}
