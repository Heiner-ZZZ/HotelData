import { ChangeDetectionStrategy, Component, HostListener, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ToastService } from '../../../../shared/services/toast.service';
import type {
  OfferEditPayload,
  PromotionAppliesScope,
  PromotionEstimateDto,
  PromotionHistoryDto,
  PromotionHistoryItemDto,
  PromotionOfferStatus,
  PromotionOptionsDto,
  PromotionRecipientsDto,
  PromotionSegment,
  PromotionSendPayload,
  PromotionSendResponseDto,
} from '../../models/marketing.dto';
import { MarketingApiService } from '../../services/marketing-api.service';
import {
  parseCouponConflict,
  type CouponConflict,
} from '../../../../shared/utils/coupon-conflict.util';

@Component({
  selector: 'app-promotions-page',
  imports: [DatePipe, EmptyStateComponent, PageHeaderComponent, PropertySelectorComponent],
  templateUrl: './promotions-page.html',
  styleUrl: './promotions-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PromotionsPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(MarketingApiService);
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly toast = inject(ToastService);
  private readonly confirmDialog = inject(ConfirmDialogService);

  // ── Route params as signals ──
  readonly selectedPropId = toSignal(
    this.route.queryParamMap.pipe(
      map((params) => Number(params.get('prop_id') ?? '0')),
      distinctUntilChanged(),
    ),
    { initialValue: 0 }
  );

  readonly selectedLabel = computed(() => this.propertyCtx.currentPropLabel());

  // ── Live recipient estimate (Mailchimp-style) ──
  readonly estimateResource = httpResource<PromotionEstimateDto>(() => {
    const propId = this.selectedPropId();
    if (!propId) return undefined;
    return {
      url: `/api/notifications/promotions/estimate?prop_id=${propId}`,
      method: 'GET',
      withCredentials: true,
    };
  });

  readonly recipientsCount = computed(() => this.estimateResource.value()?.count ?? 0);
  readonly estimateLoading = computed(() => this.estimateResource.isLoading());

  // ── Fase 2: detalles de la oferta (applies_to tarifas + cupones) ──
  readonly publicMessage = signal('');
  readonly validityStart = signal('');
  readonly validityEnd = signal('');
  readonly segment = signal<PromotionSegment>('all');
  readonly appliesToScope = signal<PromotionAppliesScope>('property');
  readonly selectedPlans = signal<string[]>([]);
  /** Modo de cupón: ninguno | vincular campaña de Tarifas | crear uno nuevo.
   *  Tarifas es la ÚNICA fuente de verdad de códigos: vincular referencia la
   *  campaña existente (no crea cupones); crear solo si el código es nuevo. */
  readonly couponMode = signal<'none' | 'link' | 'create'>('none');
  readonly promoCode = signal('');
  readonly discountPercent = signal<number | null>(null);
  readonly linkedCampaignId = signal('');

  /** Conflicto de código reportado por el BACKEND tras un envío rechazado
   *  (400 ``COUPON_CODE_EXISTS``). Es ESTRUCTURADO: trae el ``campaign_id``
   *  de la campaña dueña para poder ofrecer «Vincular esta campaña» sin
   *  parsear el texto del mensaje. */
  readonly couponConflict = signal<CouponConflict | null>(null);

  /** Código cuyo aviso fue descartado: mientras el código siga siendo este,
   *  el conflicto proactivo no reaparece (el usuario ya lo vio y lo cerró).
   *  Cambiar de código o de modo rehabilita la detección. */
  readonly suppressedConflictCode = signal('');

  /** Conflicto detectado PROACTIVAMENTE mientras se escribe el código: el
   *  código ya es el cupón principal de una campaña del hotel en el selector
   *  «Vincular» (las options ya están cargadas). El envío se rechazaría de
   *  todos modos (guard anti-robo) — mejor avisar antes. */
  readonly proactiveConflict = computed<CouponConflict | null>(() => {
    if (this.couponMode() !== 'create') return null;
    const code = this.promoCode().trim().toUpperCase();
    if (!code || this.suppressedConflictCode() === code) return null;
    const hit = this.couponCampaignOptions().find(
      (c) => c.coupon_code.toUpperCase() === code,
    );
    return hit
      ? {
          code: hit.coupon_code,
          campaign_id: hit.campaign_id,
          campaign_name: hit.name,
          message: `El código ${hit.coupon_code} ya existe en la campaña «${hit.name}» de Tarifas.`,
        }
      : null;
  });

  /** Conflicto visible: el del backend gana (es la autoridad, cubre códigos
   *  de campañas de OTROS hoteles que las options no listan); si no hay, el
   *  proactivo detectado al escribir. */
  readonly activeConflict = computed(
    () => this.couponConflict() ?? this.proactiveConflict(),
  );

  /** Planes tarifarios del hotel para el selector «Aplica a» (solo lectura). */
  readonly optionsResource = httpResource<PromotionOptionsDto>(() => {
    const propId = this.selectedPropId();
    if (!propId) return undefined;
    return {
      url: `/api/notifications/promotions/options?prop_id=${propId}`,
      method: 'GET',
      withCredentials: true,
    };
  });

  readonly ratePlanOptions = computed(() => this.optionsResource.value()?.rate_plans ?? []);
  /** Campañas de cupones del hotel (la sección «Promociones» de Tarifas) —
   *  para VINCULAR una existente en vez de crear una duplicada. */
  readonly couponCampaignOptions = computed(
    () => this.optionsResource.value()?.campaigns ?? [],
  );
  readonly optionsLoading = computed(() => this.optionsResource.isLoading());

  /** Campaña seleccionada en modo vincular (null si no hay selección). */
  readonly linkedCampaign = computed(
    () =>
      this.couponCampaignOptions().find(
        (c) => c.campaign_id === this.linkedCampaignId(),
      ) ?? null,
  );

  /** Código + descuento que la oferta pública mostrará, según el modo:
   *  - link → de la campaña seleccionada (derivado en el backend).
   *  - create → del input (solo si código y descuento son válidos).
   *  - none → null (la oferta no lleva cupón). */
  readonly couponPreview = computed<{ code: string; discount: number } | null>(() => {
    if (this.couponMode() === 'link') {
      const c = this.linkedCampaign();
      return c ? { code: c.coupon_code, discount: c.discount_percent } : null;
    }
    if (this.couponMode() === 'create') {
      const code = this.promoCode().trim();
      if (!code || this.promoCodeInvalid()) return null;
      return { code: code.toUpperCase(), discount: this.discountPercent() ?? 0 };
    }
    return null;
  });

  /** El cupón bloquea el envío cuando el modo elegido quedó incompleto:
   *  - link sin campaña seleccionada → inválido (no se puede enviar a ciegas).
   *  - create con código sin descuento válido → inválido. */
  readonly couponInvalid = computed(() => {
    if (this.couponMode() === 'link') return !this.linkedCampaignId();
    if (this.couponMode() === 'create') return this.promoCodeInvalid();
    return false;
  });

  /** Cambia el modo de cupón y limpia los campos del modo anterior (un solo
   *  camino a la vez: vincular O crear O ninguno). */
  setCouponMode(mode: 'none' | 'link' | 'create'): void {
    this.promoCode.set('');
    this.discountPercent.set(null);
    this.linkedCampaignId.set('');
    this.couponConflict.set(null);
    this.suppressedConflictCode.set('');
    this.couponMode.set(mode);
  }

  /** Input del código: editar el código invalida un conflicto previo del
   *  backend y rehabilita la detección (el usuario cambió de idea). */
  onPromoCodeInput(value: string): void {
    this.promoCode.set(value);
    this.couponConflict.set(null);
    this.suppressedConflictCode.set('');
  }

  /** «Vincular esta campaña» desde el banner: pasa a modo vincular y
   *  preselecciona la campaña dueña del código (si está en el selector).
   *  Si la campaña es de otro hotel (no aparece en las options), solo cambia
   *  al modo vincular y el usuario elige de la lista. */
  linkConflictedCampaign(): void {
    const conflict = this.activeConflict();
    if (!conflict) return;
    const known = this.couponCampaignOptions().some(
      (c) => c.campaign_id === conflict.campaign_id,
    );
    this.setCouponMode('link');
    if (known) this.linkedCampaignId.set(conflict.campaign_id);
  }

  /** Descarta el aviso para el código actual (reactivo y proactivo). Un
   *  nuevo rechazo del backend vuelve a mostrarlo — es la autoridad. */
  dismissCouponConflict(): void {
    this.couponConflict.set(null);
    this.suppressedConflictCode.set(this.promoCode().trim().toUpperCase());
  }


  /** ¿El usuario compuso detalles de oferta? (define si el payload lleva el bloque). */
  readonly hasOfferDetails = computed(
    () =>
      !!this.publicMessage().trim()
      || !!this.validityStart()
      || !!this.validityEnd()
      || this.segment() !== 'all'
      || this.appliesToScope() === 'rate_plans'
      || this.selectedPlans().length > 0
      || this.couponMode() === 'link'
      || (this.couponMode() === 'create' && !!this.promoCode().trim()),
  );

  /** Código sin descuento (o descuento fuera de 1-100) bloquea el envío. */
  readonly promoCodeInvalid = computed(() => {
    const code = this.promoCode().trim();
    if (!code) return false;
    const disc = this.discountPercent();
    return disc === null || disc < 1 || disc > 100;
  });

  /** Etiqueta humana del «aplica a» para el resumen y la vista previa. */
  readonly appliesToLabel = computed(() => {
    if (this.appliesToScope() === 'property') return 'Toda la propiedad';
    const names = this.ratePlanOptions()
      .filter((p) => this.selectedPlans().includes(p.rate_plan_id))
      .map((p) => p.name);
    return names.length ? names.join(', ') : 'Planes seleccionados';
  });

  togglePlan(planId: string): void {
    this.selectedPlans.update((ids) =>
      ids.includes(planId) ? ids.filter((id) => id !== planId) : [...ids, planId],
    );
  }

  /** Parse del input de descuento ('' → null; inválido → null). */
  parseDiscount(raw: string): number | null {
    if (raw === '') return null;
    const n = Number(raw);
    return Number.isFinite(n) ? n : null;
  }

  // ── Historial de envíos (agrupado por campaña, más reciente primero) ──
  // Filtrado por el hotel seleccionado: el backend impone el scope del
  // marketing hotelero (solo sus assigned_hotels), el prop_id del cliente
  // puede acotar pero nunca ampliar.
  readonly historyResource = httpResource<PromotionHistoryDto>(() => {
    const propId = this.selectedPropId();
    const query = propId ? `&prop_id=${propId}` : '';
    return `/api/notifications/promotions/history?page=1&page_size=20${query}`;
  });

  readonly historyItems = computed(() => this.historyResource.value()?.items ?? []);
  readonly historyLoading = computed(() => this.historyResource.isLoading());

  /** Nombre del hotel cuyo historial se muestra (vacío = todos). */
  readonly historyScopeLabel = computed(() =>
    this.selectedPropId() ? this.selectedLabel() : '',
  );

  /** Total de campañas del hotel filtrado — viene del backend (``total``),
   *  que ya respeta el scope del marketing hotelero (solo sus assigned_hotels).
   *  No depende de las filas renderizadas: con paginación, el total real
   *  puede ser mayor que ``items.length``. */
  readonly historyTotal = computed(() => this.historyResource.value()?.total ?? 0);

  /** True cuando el historial ya respondió (evita un flash de "0" en el
   *  contador mientras carga). */
  readonly historyReady = computed(() => this.historyResource.hasValue());

  /** Tooltip/aria del chip de scope: «N campañas en <hotel>». */
  readonly historyScopeTitle = computed(() => {
    const n = this.historyTotal();
    return `${n} ${n === 1 ? 'campaña' : 'campañas'} en ${this.historyScopeLabel()}`;
  });

  // ── Detalle de campaña (clic en fila → mensaje completo + destinatarios) ──
  /** Campaña cuyo detalle está abierto (null = modal cerrado). */
  readonly detailCampaign = signal<PromotionHistoryItemDto | null>(null);

  readonly detailResource = httpResource<PromotionRecipientsDto>(() => {
    const item = this.detailCampaign();
    if (!item?.campaign_id) return undefined;
    return `/api/notifications/promotions/${item.campaign_id}/recipients`;
  });

  readonly detail = computed(() => this.detailResource.value());
  readonly detailLoading = computed(
    () => this.detailResource.isLoading() && !this.detailResource.value(),
  );

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.closeDetail();
    this.closeEdit();
  }

  /** Abre el detalle de una campaña del historial (mensaje + destinatarios). */
  openDetail(item: PromotionHistoryItemDto): void {
    if (!item.campaign_id) return; // filas legacy sin id no tienen detalle
    this.detailCampaign.set(item);
  }

  closeDetail(): void {
    this.detailCampaign.set(null);
  }

  // ── Composer form (plain signals, no FormBuilder — convención del proyecto) ──
  readonly title = signal('');
  readonly message = signal('');
  /** Valor del input datetime-local ("YYYY-MM-DDTHH:mm", hora local). '' = envío inmediato. */
  readonly scheduleAt = signal('');

  readonly titleValid = computed(() => this.title().trim().length >= 3);
  readonly messageValid = computed(() => this.message().trim().length >= 10);

  /** ISO UTC de la fecha local elegida (null si no hay fecha programada). */
  readonly scheduleIso = computed(() => {
    const raw = this.scheduleAt();
    return raw ? new Date(raw).toISOString() : null;
  });

  readonly isScheduled = computed(() => this.scheduleIso() !== null);

  /** Valor mínimo aceptable para el input datetime-local (ahora, hora local). */
  readonly nowMin = computed(() => {
    const d = new Date();
    d.setSeconds(0, 0);
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  });

  /** Everything ready to review: hotel + título + mensaje + al menos un
   *  opt-in, y el código promocional (si va) tiene su descuento válido. */
  readonly canSend = computed(
    () =>
      !!this.selectedPropId()
      && this.titleValid()
      && this.messageValid()
      && this.recipientsCount() > 0
      && !this.couponInvalid(),
  );

  // ── Send lifecycle ──
  readonly sending = signal(false);
  readonly sentResult = signal<PromotionSendResponseDto | null>(null);

  onPropSelected(event: { propId: number; label: string }): void {
    if (!event.propId) {
      this.propertyCtx.clear();
    } else {
      this.propertyCtx.setProperty(event.propId, event.label || `Propiedad #${event.propId}`);
    }
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null }
    });
  }

  /** Pre-send gate: confirmation with the exact recipient count (o fecha). */
  async reviewAndSend(): Promise<void> {
    if (!this.canSend()) return;
    const count = this.recipientsCount();
    const scheduled = this.isScheduled();
    const when = scheduled ? this.formatIso(this.scheduleIso()!) : null;
    const details = [
      'Solo lo recibirán los huéspedes con consentimiento de marketing activo en este hotel.',
      scheduled
        ? 'Se enviará automáticamente a la hora indicada (hora local del navegador).'
        : 'Llega a la campanita del huésped y, en segundo plano, a su correo.',
    ];
    if (this.hasOfferDetails()) {
      const offerLines = [
        'También se publicará como oferta en la página del hotel.',
      ];
      if (this.publicMessage().trim()) {
        offerLines.push(`Descripción pública: ${this.publicMessage().trim()}`);
      }
      const coupon = this.couponPreview();
      if (coupon) {
        offerLines.push(
          this.couponMode() === 'link'
            ? `Cupón vinculado de Tarifas: ${coupon.code} · ${coupon.discount}% (no se crea uno nuevo).`
            : `Código ${coupon.code} · ${coupon.discount}% de descuento (cupón en Tarifas).`,
        );
      }
      details.push(...offerLines);
    }
    const ok = await this.confirmDialog.open({
      title: scheduled ? 'Programar promoción' : 'Enviar promoción',
      message: scheduled
        ? `¿Programar «${this.title().trim()}» para el ${when}?`
        : `¿Enviar «${this.title().trim()}» a ${count} ${count === 1 ? 'huésped' : 'huéspedes'}?`,
      details,
      confirmLabel: scheduled ? 'Programar' : 'Enviar',
      cancelLabel: 'Cancelar',
      variant: 'default',
    });
    if (!ok) return;

    this.sending.set(true);
    this.sentResult.set(null);
    const payload: PromotionSendPayload = {
      title: this.title().trim(),
      message: this.message().trim(),
      prop_id: this.selectedPropId(),
    };
    const scheduledIso = this.scheduleIso();
    if (scheduledIso) {
      payload.send_at = scheduledIso; // solo viaja cuando se programa
    }
    if (this.hasOfferDetails()) {
      const publicMessage = this.publicMessage().trim();
      if (publicMessage) payload.public_message = publicMessage;
      if (this.validityStart()) payload.validity_start = this.validityStart();
      if (this.validityEnd()) payload.validity_end = this.validityEnd();
      payload.segment = this.segment();
      payload.applies_to_scope = this.appliesToScope();
      if (this.appliesToScope() === 'rate_plans' && this.selectedPlans().length) {
        payload.rate_plan_ids = this.selectedPlans();
      }
      if (this.couponMode() === 'link' && this.linkedCampaignId()) {
        // Vincular: la campaña ya existe en Tarifas — el backend deriva
        // código y descuento de ella; NO se crean cupones nuevos.
        payload.coupon_campaign_id = this.linkedCampaignId();
      } else if (this.couponMode() === 'create') {
        const code = this.promoCode().trim();
        if (code) {
          payload.promo_code = code;
          payload.discount_percent = this.discountPercent()!;
        }
      }
    }
    this.api.sendPromotion(payload).subscribe({
        next: (res) => {
          this.sending.set(false);
          this.sentResult.set(res);
          this.couponConflict.set(null);
          this.suppressedConflictCode.set('');
          this.title.set('');
          this.message.set('');
          this.scheduleAt.set('');
          this.publicMessage.set('');
          this.validityStart.set('');
          this.validityEnd.set('');
          this.segment.set('all');
          this.appliesToScope.set('property');
          this.selectedPlans.set([]);
          this.promoCode.set('');
          this.discountPercent.set(null);
          this.linkedCampaignId.set('');
          this.couponMode.set('none');
          this.historyResource.reload(); // el envío nuevo aparece al instante en el historial
          if (res.scheduled) {
            this.toast.success(`Promoción programada para ${this.formatIso(res.send_at_iso ?? '')}`);
          } else {
            this.toast.success(`Promoción enviada a ${res.sent} ${res.sent === 1 ? 'huésped' : 'huéspedes'}`);
          }
        },
        error: (error: ApiError) => {
          this.sending.set(false);
          const conflict = parseCouponConflict(error);
          if (conflict) {
            // Banner destacado y accionable — reemplaza el toast del envío
            // (el interceptor global igual avisa con un toast efímero).
            this.couponConflict.set(conflict);
            return;
          }
          this.toast.error(error.message || 'No fue posible enviar la promoción.');
        },
      });
  }

  // ── Historial: labels de status + cancelación ──

  statusLabel(item: PromotionHistoryItemDto): string {
    const map: Record<string, string> = {
      sent: 'Enviada',
      pending: 'Programada',
      canceled: 'Cancelada',
      error: 'Error',
    };
    return map[item.status ?? 'sent'] ?? 'Enviada';
  }

  statusTone(item: PromotionHistoryItemDto): string {
    const map: Record<string, string> = {
      sent: 'success',
      pending: 'accent',
      canceled: 'neutral',
      error: 'danger',
    };
    return map[item.status ?? 'sent'] ?? 'success';
  }

  statusIcon(item: PromotionHistoryItemDto): string {
    const map: Record<string, string> = {
      sent: 'check_circle',
      pending: 'schedule',
      canceled: 'block',
      error: 'error',
    };
    return map[item.status ?? 'sent'] ?? 'check_circle';
  }

  canCancel(item: PromotionHistoryItemDto): boolean {
    return item.status === 'pending';
  }

  /** La fila abre el detalle solo cuando tiene campaign_id (no legacy). */
  canOpenDetail(item: PromotionHistoryItemDto): boolean {
    return !!item.campaign_id;
  }

  /** Enter/Espacio en la fila clickeable (a11y: no desplaza la página). */
  onRowKey(item: PromotionHistoryItemDto, event: Event): void {
    if (!this.canOpenDetail(item)) return;
    (event as KeyboardEvent).preventDefault();
    this.openDetail(item);
  }

  // ── Edición + pausa/reactivación de la oferta pública (Fase 3) ──
  // La ENTIDAD ``promotions`` se edita sin re-enviar (la campanita del
  // huésped no se toca) y la oferta se puede pausar/reactivar en la página
  // pública. El estado de la oferta llega en ``offer_status`` del historial.

  /** Campaña cuya oferta está en edición (null = modal cerrado). */
  readonly editingCampaign = signal<PromotionHistoryItemDto | null>(null);
  readonly savingOffer = signal(false);

  // Form de edición (independiente del composer — se pre-llena desde la entidad).
  readonly editPublicMessage = signal('');
  readonly editValidityStart = signal('');
  readonly editValidityEnd = signal('');
  readonly editSegment = signal<PromotionSegment>('all');
  readonly editAppliesScope = signal<PromotionAppliesScope>('property');
  readonly editSelectedPlans = signal<string[]>([]);

  /** Planes del hotel de la campaña en edición — independiente del selector
   *  superior (el marketing puede editar una oferta de otro de sus hoteles). */
  readonly editOptionsResource = httpResource<PromotionOptionsDto>(() => {
    const item = this.editingCampaign();
    if (!item?.prop_id) return undefined;
    return {
      url: `/api/notifications/promotions/options?prop_id=${item.prop_id}`,
      method: 'GET',
      withCredentials: true,
    };
  });

  readonly editRatePlans = computed(() => this.editOptionsResource.value()?.rate_plans ?? []);
  readonly editOptionsLoading = computed(() => this.editOptionsResource.isLoading());

  /** La entidad existe (active/paused) → se puede editar; solo activa se
   *  puede pausar; solo pausada se puede reactivar. */
  canEditOffer(item: PromotionHistoryItemDto): boolean {
    return item.offer_status === 'active' || item.offer_status === 'paused';
  }

  canPause(item: PromotionHistoryItemDto): boolean {
    return item.offer_status === 'active';
  }

  canResume(item: PromotionHistoryItemDto): boolean {
    return item.offer_status === 'paused';
  }

  offerStatusLabel(item: PromotionHistoryItemDto): string {
    const map: Record<string, string> = {
      paused: 'Pausada',
      active: 'Activa',
      scheduled: 'Programada',
      canceled: 'Cancelada',
    };
    return map[item.offer_status ?? ''] ?? '';
  }

  /** Abre el modal de edición pre-llenado con los campos de la entidad. */
  openEdit(item: PromotionHistoryItemDto): void {
    if (!this.canEditOffer(item)) return;
    this.editPublicMessage.set(item.public_message ?? '');
    this.editValidityStart.set(item.validity?.start_date ?? '');
    this.editValidityEnd.set(item.validity?.end_date ?? '');
    this.editSegment.set(item.segment?.audience ?? 'all');
    this.editAppliesScope.set(item.applies_to?.scope ?? 'property');
    this.editSelectedPlans.set(item.applies_to?.rate_plan_ids ?? []);
    this.editingCampaign.set(item);
  }

  closeEdit(): void {
    if (this.savingOffer()) return;
    this.editingCampaign.set(null);
  }

  toggleEditPlan(planId: string): void {
    this.editSelectedPlans.update((ids) =>
      ids.includes(planId) ? ids.filter((id) => id !== planId) : [...ids, planId],
    );
  }

  /** Etiqueta del «aplica a» dentro del modal de edición. */
  readonly editAppliesLabel = computed(() => {
    if (this.editAppliesScope() === 'property') return 'Toda la propiedad';
    const names = this.editRatePlans()
      .filter((p) => this.editSelectedPlans().includes(p.rate_plan_id))
      .map((p) => p.name);
    return names.length ? names.join(', ') : 'Planes seleccionados';
  });

  /** Guarda la edición SIN re-enviar: solo actualiza la entidad (mensaje
   *  público, validez, segmento, aplica-a). El código + descuento no son
   *  editables aquí — el cupón vive en Tarifas. */
  saveEdit(): void {
    const item = this.editingCampaign();
    if (!item || this.savingOffer()) return;
    this.savingOffer.set(true);
    const payload: OfferEditPayload = {
      public_message: this.editPublicMessage().trim(),
      validity_start: this.editValidityStart() || undefined,
      validity_end: this.editValidityEnd() || undefined,
      segment: this.editSegment(),
      applies_to_scope: this.editAppliesScope(),
      rate_plan_ids:
        this.editAppliesScope() === 'rate_plans' ? this.editSelectedPlans() : [],
    };
    this.api.updateOffer(item.campaign_id, payload).subscribe({
      next: () => {
        this.savingOffer.set(false);
        this.editingCampaign.set(null);
        this.toast.success('Oferta actualizada');
        this.historyResource.reload();
      },
      error: (error: ApiError) => {
        this.savingOffer.set(false);
        this.toast.error(error.message || 'No fue posible actualizar la oferta.');
      },
    });
  }

  /** Pausa (con confirmación) o reactiva la oferta pública. Nunca toca lo ya
   *  enviado: solo el estado de la ENTIDAD (la página pública la oculta). */
  async togglePublic(item: PromotionHistoryItemDto): Promise<void> {
    const pausing = this.canPause(item);
    if (pausing) {
      const ok = await this.confirmDialog.open({
        title: 'Pausar oferta',
        message: `¿Pausar «${item.title}»?`,
        details: [
          'Desaparecerá de la página pública del hotel hasta que la reactives.',
          'Los huéspedes que ya la recibieron conservan su notificación en la campanita.',
        ],
        confirmLabel: 'Pausar',
        cancelLabel: 'Volver',
        variant: 'warning',
      });
      if (!ok) return;
    }
    const active = !pausing; // resume sin confirmación (reversible y sin riesgo)
    this.api.setOfferPublic(item.campaign_id, active).subscribe({
      next: () => {
        this.toast.success(active ? 'Oferta reactivada' : 'Oferta pausada');
        this.historyResource.reload();
      },
      error: (error: ApiError) => {
        this.toast.error(error.message || 'No fue posible actualizar la oferta.');
      },
    });
  }

  /** Oferta pausada → la fila se marca para que el marketing la distinga. */
  isOfferPaused(item: PromotionHistoryItemDto): boolean {
    return item.offer_status === 'paused';
  }

  offerStatusBadgeTone(item: PromotionHistoryItemDto): string {
    const tones: Record<string, string> = {
      pending: 'accent',
      scheduled: 'accent',
      active: 'success',
      paused: 'neutral',
      canceled: 'neutral',
    };
    return tones[item.offer_status ?? ''] ?? 'neutral';
  }

  displayDate(item: PromotionHistoryItemDto): string | null {
    return item.sent_at_iso || item.send_at_iso || null;
  }

  /** Cancelar una promoción aún pendiente en la cola (con confirmación). */
  async cancelPromotion(campaignId: string): Promise<void> {
    const ok = await this.confirmDialog.open({
      title: 'Cancelar envío programado',
      message: '¿Cancelar esta promoción antes de que se envíe?',
      details: [
        'Los huéspedes no recibirán nada. La campaña quedará marcada como cancelada en el historial.',
      ],
      confirmLabel: 'Cancelar envío',
      cancelLabel: 'Volver',
      variant: 'warning',
    });
    if (!ok) return;
    this.api.cancelPromotion(campaignId).subscribe({
      next: () => {
        this.toast.success('Promoción cancelada');
        this.historyResource.reload();
      },
      error: (error: ApiError) => {
        this.toast.error(error.message || 'No fue posible cancelar la promoción.');
      },
    });
  }

  resetResult(): void {
    this.sentResult.set(null);
  }

  private formatIso(iso: string): string {
    const d = new Date(iso);
    return Number.isNaN(d.getTime())
      ? iso
      : d.toLocaleString('es', { dateStyle: 'medium', timeStyle: 'short' });
  }
}
