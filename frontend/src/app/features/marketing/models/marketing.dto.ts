/**
 * DTOs del envío de promociones (marketing).
 *
 * Espejo de `server/src/app/modules/notifications/routes.py`:
 * - `GET /api/notifications/promotions/estimate?prop_id=`
 * - `POST /api/notifications/promotions` (envío inmediato o programado)
 * - `POST /api/notifications/promotions/{campaign_id}/cancel`
 * - `GET /api/notifications/promotions/history`
 */

export interface PromotionEstimateDto {
  count: number;
  prop_id: number | null;
  notification_type: string;
}

export type PromotionSegment = 'all' | 'families' | 'couples' | 'business';

export type PromotionAppliesScope = 'property' | 'rate_plans';

export interface PromotionSendPayload {
  title: string;
  message: string;
  prop_id?: number;
  /** Fecha/hora de envío (ISO UTC). Futura → se programa; null/ausente → inmediato. */
  send_at?: string | null;
  // ── Fase 2: detalles de la oferta (opcionales) ──
  /** Descripción pública en la página del hotel (sin PII). */
  public_message?: string;
  /** Inicio de la ventana de validez (YYYY-MM-DD). */
  validity_start?: string;
  /** Fin de la ventana de validez (YYYY-MM-DD). */
  validity_end?: string;
  segment?: PromotionSegment;
  /** Alcance de «Aplica a»: toda la propiedad o planes tarifarios concretos. */
  applies_to_scope?: PromotionAppliesScope;
  /** Planes tarifarios a los que aplica (scope=rate_plans). */
  rate_plan_ids?: string[];
  /** Código promocional — crea el cupón en Tarifas junto al descuento. */
  promo_code?: string;
  discount_percent?: number;
  /** Campaña de cupones de Tarifas a VINCULAR (no crea cupones: código y
   *  descuento se derivan de la campaña existente). Mutuamente excluyente
   *  con promo_code + discount_percent. */
  coupon_campaign_id?: string;
}

/** Plan tarifario para el selector «Aplica a» (GET /promotions/options). */
export interface PromotionRatePlanOptionDto {
  rate_plan_id: string;
  name: string;
  base_rate?: number;
  room_type_labels: string[];
}

/** Campaña de cupones de Tarifas para el selector «Vincular» (la sección
 *  «Promociones» de Tarifas — única fuente de verdad de códigos). */
export interface PromotionCouponCampaignOptionDto {
  campaign_id: string;
  name: string;
  discount_percent: number;
  coupon_code: string;
  is_active?: boolean;
}

export interface PromotionOptionsDto {
  prop_id: number;
  rate_plans: PromotionRatePlanOptionDto[];
  /** Campañas de cupones del hotel (vincular en vez de crear duplicados). */
  campaigns: PromotionCouponCampaignOptionDto[];
}

export interface PromotionSendResponseDto {
  notification_type: string;
  sent: number;
  skipped: number;
  recipients: string[];
  scheduled?: boolean;
  campaign_id?: string | null;
  send_at_iso?: string | null;
}

export type PromotionStatus = 'sent' | 'pending' | 'canceled' | 'error';

/** Estado de la ENTIDAD ``promotions`` (la oferta pública). El estado de la
 *  fila de la campanita sigue siendo ``status`` (sent/read). */
export type PromotionOfferStatus =
  | 'pending'
  | 'scheduled'
  | 'active'
  | 'paused'
  | 'canceled';

export interface PromotionOfferValidityDto {
  start_date?: string;
  end_date?: string;
}

export interface PromotionOfferAppliesDto {
  scope?: PromotionAppliesScope;
  rate_plan_ids?: string[];
}

export interface PromotionOfferSegmentDto {
  audience?: PromotionSegment;
}

/** Campos de la entidad ``promotions`` presentes en historial y detalle,
 *  para pre-llenar el modal de edición sin un fetch extra. */
export interface PromotionOfferEntityFields {
  offer_status?: PromotionOfferStatus;
  public_message?: string;
  validity?: PromotionOfferValidityDto | null;
  applies_to?: PromotionOfferAppliesDto | null;
  segment?: PromotionOfferSegmentDto | null;
  promo_code?: string | null;
  discount_percent?: number | null;
  /** Campaña de Tarifas vinculada (si la oferta no creó cupones propios). */
  coupon_campaign_id?: string | null;
}

export interface PromotionHistoryItemDto extends PromotionOfferEntityFields {
  campaign_id: string;
  title: string;
  message: string;
  prop_id: number;
  hotel_name: string;
  sent_at_iso?: string | null;
  send_at_iso?: string | null;
  recipient_count: number;
  recipients: string[];
  email_sent: number;
  /** sent=Enviada · pending=Programada · canceled=Cancelada · error=Error */
  status?: PromotionStatus;
}

export interface PromotionHistoryDto {
  items: PromotionHistoryItemDto[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PromotionCancelResponseDto {
  campaign_id: string;
  canceled: boolean;
}

export interface PromotionRecipientDto {
  email: string;
  name: string;
  /** True si el huésped abrió/leyó la promoción (dot de la campanita). */
  is_read: boolean;
  read_at_iso?: string | null;
}

export interface PromotionRecipientsDto extends PromotionOfferEntityFields {
  campaign_id: string;
  title: string;
  message: string;
  prop_id: number;
  hotel_name: string;
  status: PromotionStatus;
  sent_at_iso?: string | null;
  send_at_iso?: string | null;
  recipient_count: number;
  email_sent: number;
  recipients: PromotionRecipientDto[];
}

/** Body de ``PUT /promotions/{campaign_id}/offer`` — edita la entidad SIN
 *  re-enviar. Solo los campos presentes se actualizan ('' limpia validez). */
export interface OfferEditPayload {
  public_message?: string;
  validity_start?: string;
  validity_end?: string;
  segment?: PromotionSegment;
  applies_to_scope?: PromotionAppliesScope;
  rate_plan_ids?: string[];
}

export interface OfferToggleResponseDto {
  campaign_id: string;
  offer_status: PromotionOfferStatus;
  active: boolean;
}
