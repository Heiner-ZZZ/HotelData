import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';

import { catchAuthError } from '../../../shared/utils/catch-auth-error';
import type {
  OfferEditPayload,
  OfferToggleResponseDto,
  PromotionCancelResponseDto,
  PromotionOfferAppliesDto,
  PromotionOfferSegmentDto,
  PromotionOfferValidityDto,
  PromotionSendPayload,
  PromotionSendResponseDto,
} from '../models/marketing.dto';

@Injectable({ providedIn: 'root' })
export class MarketingApiService {
  private readonly http = inject(HttpClient);

  /** Send a promotional notification to opted-in guests only (POST). */
  sendPromotion(payload: PromotionSendPayload) {
    return this.http
      .post<PromotionSendResponseDto>('/notifications/promotions', payload)
      .pipe(catchAuthError());
  }

  /** Cancel a queued (scheduled) promotion before it is sent (POST). */
  cancelPromotion(campaignId: string) {
    return this.http
      .post<PromotionCancelResponseDto>(`/notifications/promotions/${campaignId}/cancel`, {})
      .pipe(catchAuthError());
  }

  /** Edit the ``promotions`` entity of a sent campaign WITHOUT re-sending
   *  (public message, validity window, segment, «aplica a»). */
  updateOffer(campaignId: string, payload: OfferEditPayload) {
    return this.http
      .put<PromotionOfferEntityWire>(`/notifications/promotions/${campaignId}/offer`, payload)
      .pipe(catchAuthError());
  }

  /** Pause (``active=false``) or resume (``active=true``) the public offer.
   *  Only flips the entity — the already-sent bell rows stay untouched. */
  setOfferPublic(campaignId: string, active: boolean) {
    return this.http
      .post<OfferToggleResponseDto>(
        `/notifications/promotions/${campaignId}/offer/toggle-public`,
        { active },
      )
      .pipe(catchAuthError());
  }
}

/** Wire shape returned by the edit endpoint (mirror of ``_offer_entity_wire``). */
interface PromotionOfferEntityWire {
  promotion_id: string;
  campaign_id: string;
  prop_id: number;
  title: string;
  public_message: string;
  offer_status: string;
  validity: PromotionOfferValidityDto | null;
  segment: PromotionOfferSegmentDto | null;
  applies_to: PromotionOfferAppliesDto | null;
  promo_code: string | null;
  discount_percent: number | null;
  coupon_campaign_id?: string | null;
}
