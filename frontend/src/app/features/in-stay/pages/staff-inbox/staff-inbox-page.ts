import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, inject, signal } from '@angular/core';
import { DatePipe, CurrencyPipe, formatCurrency } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription } from 'rxjs';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { InStayApiService } from '../../services/in-stay-api.service';
import { ExpensesApiService } from '../../../expenses/services/expenses-api.service';
import { StaySseService } from '../../services/stay-sse.service';
import { FolioPaymentModalComponent } from '../../components/folio-payment-modal/folio-payment-modal';
import { FolioTransactionsModalComponent } from '../../components/folio-transactions-modal/folio-transactions-modal';
import { InfoTooltipComponent } from '../../../../shared/ui/info-tooltip/info-tooltip.component';
import { Conversation, ChatMessage, ServiceRequest, StaySession, LostItem } from '../../models/in-stay.model';
import type { LedgerFolio } from '../../../expenses/models/ledger.model';

import type { MainTab, TimelineItem } from './staff-inbox-page.types';
import { REQUEST_CATEGORIES } from './staff-inbox-page.constants';

/** Build the unified timeline from conversations + requests. */
function buildTimeline(
  conversations: Conversation[],
  requests: ServiceRequest[],
  categoryFilter: string | null,
): TimelineItem[] {
  const items: TimelineItem[] = [];

  for (const c of conversations) {
    items.push({
      type: 'message',
      id: c._id,
      roomLabel: c._id,
      guestName: c.guest_name,
      preview: c.last_message,
      time: c.last_time,
      unread: c.unread,
    });
  }

  const filteredRequests = categoryFilter
    ? requests.filter((r) => r.request_type === categoryFilter)
    : requests;

  for (const r of filteredRequests) {
    items.push({
      type: 'request',
      id: r._id,
      roomLabel: r.room_label,
      guestName: '',
      preview: r.description || r.request_type_label,
      time: r.created_at,
      status: r.status,
      statusLabel: r.status_label,
      requestType: r.request_type,
      request: r,
    });
  }

  // Sort by time desc
  items.sort((a, b) => b.time.localeCompare(a.time));
  return items;
}

/** Return the Material Symbols icon name for a request type. */
function getRequestIcon(type?: string): string {
  switch (type) {
    case 'housekeeping': return 'cleaning_services';
    case 'room_service': return 'room_service';
    case 'maintenance': return 'handyman';
    default: return 'concierge';
  }
}

/** Chat buckets used by the conversation filters. */
export type ChatBucket = 'active' | 'today' | 'history';

export const CHAT_BUCKET_META: readonly { id: ChatBucket; label: string; icon: string }[] = [
  { id: 'active', label: 'Activas', icon: 'bed' },
  { id: 'today', label: 'Del día', icon: 'today' },
  { id: 'history', label: 'Historial', icon: 'history' },
] as const;

/** Finalized reservation states — the guest is no longer staying. */
const FINALIZED_STATUSES = new Set(['checked_out', 'no_show', 'cancelled']);

/**
 * Classify a conversation into one of three mutually exclusive chat buckets,
 * keyed off the reservation dates (not the last message time nor a possibly
 * stuck `stay_status`):
 *  1. history — the reservation/folio is over (check_out already passed) or
 *     finalized (check-out / no-show / cancelled).
 *  2. today   — check-in or check-out happens today.
 *  3. active  — currently staying, no arrival/departure today.
 */
export function classifyConversation(conv: Conversation, today: string): ChatBucket {
  const status = (conv.stay_status ?? '').toLowerCase();
  const checkIn = (conv.check_in ?? '').slice(0, 10);
  const checkOut = (conv.check_out ?? '').slice(0, 10);

  // Reservation no longer active: date is the source of truth. `stay_status`
  // can remain `pending` after the reservation ended, so it must NOT gate this.
  if (FINALIZED_STATUSES.has(status)) return 'history';
  if (checkOut && checkOut < today) return 'history';
  if (checkIn === today || checkOut === today) return 'today';
  return 'active';
}

@Component({
  selector: 'app-staff-inbox',
  imports: [
    DatePipe,
    CurrencyPipe,
    FormsModule,
    PropertySelectorComponent,
    FolioPaymentModalComponent,
    FolioTransactionsModalComponent,
    InfoTooltipComponent,
  ],
  templateUrl: './staff-inbox-page.html',
  styleUrl: './staff-inbox-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StaffInboxPageComponent {
  /**
   * Cleanup registered via ``inject(DestroyRef).onDestroy`` in the constructor —
   * replaces the legacy ``ngOnDestroy`` lifecycle hook. SSE subscription
   * disconnect and ``document.title`` reset happen during the same destruction
   * phase in Angular 22.
   */
  // ── Dependencies ──
  private readonly api = inject(InStayApiService);
  private readonly ledgerApi = inject(ExpensesApiService);
  private readonly propCtx = inject(PropertyContextService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly sse = inject(StaySseService);
  private readonly destroyRef = inject(DestroyRef);

  // ── State ──
  readonly selectedPropId = this.propCtx.currentPropId;
  readonly selectedLabel = signal('');
  readonly activeTab = signal<MainTab>('unified');
  readonly loading = signal(true);

  /** Route-based tab mapping. */
  private readonly tabRouteMap: Record<string, MainTab> = {
    '': 'unified',
    'folios': 'folios',
    'sessions': 'sessions',
    'lost-found': 'lost-found',
  };

  // Conversations (left sidebar)
  readonly conversations = signal<Conversation[]>([]);
  readonly selectedRoom = signal<string | null>(null);
  readonly messages = signal<ChatMessage[]>([]);
  readonly replyInput = signal('');
  readonly sendingReply = signal(false);

  // Service requests (left sidebar)
  readonly requests = signal<ServiceRequest[]>([]);
  readonly selectedRequest = signal<ServiceRequest | null>(null);
  readonly requestCategoryFilter = signal<string | null>(null);
  readonly categories = REQUEST_CATEGORIES;
  /** Bucket metadata for the chat stay-state filter chips. */
  readonly chatBucketMeta = CHAT_BUCKET_META;

  // Staff response input
  readonly staffResponseInput = signal('');

  // Extend stay date (only shown when completing an extend_stay request)
  readonly newCheckOutDate = signal('');

  /** Whether the confirm modal should show a date picker for extend_stay. */
  readonly showExtendDateField = computed(() => {
    const req = this.confirmTarget();
    return this.confirmActionType() === 'complete' && req?.request_type === 'extend_stay';
  });

  /** Disable confirm button when extend_stay date is required but empty. */
  readonly confirmDisabled = computed(() => {
    if (this.showExtendDateField() && !this.newCheckOutDate()) return true;
    return false;
  });

  /** Today's date for min attribute on date inputs. */
  get todayDate(): string {
    return new Date().toISOString().slice(0, 10);
  }

  // Confirm modal
  readonly showConfirmModal = signal(false);
  readonly confirmTitle = signal('');
  readonly confirmMessage = signal('');
  readonly confirmActionType = signal<'take' | 'complete' | 'cancel' | null>(null);
  readonly confirmTarget = signal<ServiceRequest | null>(null);

  // Booking context for quick-request creation
  readonly selectedBookingId = signal<string | null>(null);

  /** Conversation selected in the sidebar (drives the chat header attribution). */
  readonly selectedConversation = computed(() =>
    this.conversations().find((c) => c._id === this.selectedRoom()) ?? null,
  );

  /** Guest name of the open chat, shown real-chat style next to the room. */
  readonly selectedGuestName = computed(() => this.selectedConversation()?.guest_name ?? '');

  // Sessions tab
  readonly sessions = signal<StaySession[]>([]);
  readonly sessionsLoading = signal(false);
  readonly showNewSessionForm = signal(false);
  readonly newSessionBookingId = signal('');
  readonly newSessionRoomLabel = signal('');
  readonly newSessionGuestName = signal('');
  readonly newSessionCheckIn = signal('');
  readonly newSessionCheckOut = signal('');
  readonly creatingSession = signal(false);

  // Lost & Found tab
  readonly lostFoundItems = signal<LostItem[]>([]);
  readonly lostFoundLoading = signal(false);
  readonly lostFoundStatusFilter = signal<string | null>(null);
  readonly lostFoundSearch = signal('');
  readonly showLostFoundForm = signal(false);
  readonly newLostItemName = signal('');
  readonly newLostDesc = signal('');
  readonly newLostLocation = signal('');
  readonly newLostFoundBy = signal('');
  readonly newLostBookingId = signal('');
  readonly newLostGuestName = signal('');
  readonly creatingLostItem = signal(false);
  readonly selectedLostItem = signal<LostItem | null>(null);
  readonly lostReturnedTo = signal('');

  // Folios (separate tab)
  readonly folios = signal<LedgerFolio[]>([]);
  readonly foliosLoading = signal(false);
  readonly folioStatusFilter = signal('open');

  /** Estados que agrupa el chip "Cerrados": todos los folios no abiertos. */
  private readonly CLOSED_FOLIO_STATUSES = 'closed,settled,written_off';

  // Payment / transfer modal state
  readonly paymentModalFolio = signal<LedgerFolio | null>(null);
  readonly transferModalFolio = signal<LedgerFolio | null>(null);
  readonly paymentModalError = signal('');
  readonly transactionsModalFolio = signal<LedgerFolio | null>(null);

  // ── Computed ──

  /** Combined timeline sorted by last activity. */
  readonly timeline = computed(() =>
    buildTimeline(
      this.conversations(),
      this.requests(),
      this.requestCategoryFilter(),
    ),
  );

  /** Chat stay-state filter — null shows every bucket. */
  readonly chatFilter = signal<ChatBucket | null>(null);

  /** Conversations grouped into the three chat buckets. */
  readonly conversationBuckets = computed(() => {
    const buckets: Record<ChatBucket, Conversation[]> = { active: [], today: [], history: [] };
    for (const c of this.conversations()) {
      buckets[classifyConversation(c, this.todayDate)].push(c);
    }
    return buckets;
  });

  /** Bucket ids visible under the current filter (empty buckets hidden). */
  readonly visibleChatBuckets = computed(() => {
    const f = this.chatFilter();
    const buckets = this.conversationBuckets();
    const order: ChatBucket[] = ['active', 'today', 'history'];
    if (f) return buckets[f].length > 0 ? [f] : [];
    return order.filter((b) => buckets[b].length > 0);
  });

  /** Visible buckets with label/icon/conversations for the template. */
  readonly visibleChatGroups = computed(() => {
    const buckets = this.conversationBuckets();
    return this.visibleChatBuckets().map((id) => {
      const meta = CHAT_BUCKET_META.find((m) => m.id === id)!;
      return { id, label: meta.label, icon: meta.icon, conversations: buckets[id] };
    });
  });

  /** Requests (always shown in main list). */
  readonly requestItems = computed(() =>
    this.timeline().filter(item => item.type === 'request'),
  );

  /** Map room_label → conversation for DND lookup in template. */
  readonly conversationsMap = computed(() => {
    const map: Record<string, Conversation> = {};
    for (const c of this.conversations()) {
      map[c._id] = c;
    }
    return map;
  });

  /** Total unread messages across all conversations. */
  readonly unreadCount = computed(() =>
    this.conversations().reduce((sum, c) => sum + c.unread, 0),
  );

  /** Pending + in-progress requests count. */
  readonly pendingCount = computed(() =>
    this.requests().filter((r) => r.status === 'pending' || r.status === 'in_progress').length,
  );

  /** Active folios count. */
  readonly folioCount = computed(() => this.folios().length);

  readonly lostCount = computed(() => this.lostFoundItems().length);

  private sseSub: Subscription | null = null;
  private originalTitle = document.title;

  constructor() {
    // Disconnect SSE + restore the original document title when the page is
    // torn down. Co-located with the ``subscribe``/``subscribe.remove`` paths
    // because SSE lifecycle is the only resource holding async teardown work.
    this.destroyRef.onDestroy(() => {
      this.sseSub?.unsubscribe();
      this.sse.disconnect();
      document.title = this.originalTitle;
    });

    // Initial tab from the deep-link URL (read once). Tab clicks stay local
    // so switching never reloads the component.
    const segments = this.route.snapshot.url.map((s) => s.path);
    const tabSegment = segments[segments.length - 1] ?? '';
    const initialTab = this.tabRouteMap[tabSegment] ?? 'unified';
    this.activeTab.set(initialTab);
    if (initialTab === 'sessions') this.loadSessions();
    if (initialTab === 'lost-found') this.loadLostFound();

    // Auto-select property in single-hotel mode
    effect(() => {
      if (this.propCtx.ready() && this.propCtx.singleHotelMode()) {
        const propId = this.propCtx.currentPropId();
        if (propId && this.selectedPropId() !== propId) {
          this.onPropSelected({ propId, label: '' });
        }
      }
    });

    this.loadData();
    this.connectSse();
  }

  /** No-op — removed Gmail-style tab title counter per user request. */

  // ── Data loading ──

  private loadData(): void {
    // El backend exige prop_id >= 1 (Query ge=1): sin propiedad seleccionada
    // aún no hay nada que pedir — el effect de auto-selección (o el usuario)
    // disparará la carga cuando haya un id real.
    const propId = this.selectedPropId();
    if (!propId) return;

    this.loading.set(true);

    this.api.listConversations(propId).subscribe({
      next: (res) => {
        this.conversations.set(res.conversations);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });

    this.api.listRequests(propId, undefined).subscribe({
      next: (res) => this.requests.set(res.items),
    });

    this.loadFolios();
  }

  private loadFolios(): void {
    const propId = this.selectedPropId();
    if (!propId) return;

    this.foliosLoading.set(true);
    const status =
      this.folioStatusFilter() === 'closed'
        ? this.CLOSED_FOLIO_STATUSES
        : this.folioStatusFilter();
    this.ledgerApi.getLedgerFolios(propId, status).subscribe({
      next: (res) => {
        this.folios.set(res.items);
        this.foliosLoading.set(false);
      },
      error: () => this.foliosLoading.set(false),
    });
  }

  // ── Tab switching ──

  /** Switch tabs locally — no route navigation, so the interface does not reload. */
  setTab(tab: MainTab): void {
    this.activeTab.set(tab);
    if (tab === 'folios') this.loadFolios();
    if (tab === 'sessions') this.loadSessions();
    if (tab === 'lost-found') this.loadLostFound();
  }

  setFolioStatusFilter(status: string): void {
    this.folioStatusFilter.set(status);
    this.loadFolios();
  }

  // ── Sessions ──

  private loadSessions(): void {
    this.sessionsLoading.set(true);
    const propId = this.selectedPropId() ?? undefined;
    this.api.listSessions(propId).subscribe({
      next: (res) => {
        this.sessions.set(res.items);
        this.sessionsLoading.set(false);
      },
      error: () => this.sessionsLoading.set(false),
    });
  }

  createSession(): void {
    const bookingId = this.newSessionBookingId().trim();
    const roomLabel = this.newSessionRoomLabel().trim();
    const guestName = this.newSessionGuestName().trim();
    const checkIn = this.newSessionCheckIn().trim();
    const checkOut = this.newSessionCheckOut().trim();
    const propId = this.selectedPropId();

    if (!bookingId || !roomLabel || !guestName || !checkIn || !checkOut || !propId) {
      this.toast.warning('Todos los campos son requeridos.');
      return;
    }

    this.creatingSession.set(true);
    this.api.createSession({
      booking_id: bookingId,
      prop_id: propId,
      room_label: roomLabel,
      guest_name: guestName,
      check_in: checkIn,
      check_out: checkOut,
    }).subscribe({
      next: () => {
        this.toast.success('Sesión creada');
        this.showNewSessionForm.set(false);
        this.newSessionBookingId.set('');
        this.newSessionRoomLabel.set('');
        this.newSessionGuestName.set('');
        this.newSessionCheckIn.set('');
        this.newSessionCheckOut.set('');
        this.creatingSession.set(false);
        this.loadSessions();
      },
      error: (err) => {
        this.toast.error(err?.error?.detail || 'Error al crear la sesión');
        this.creatingSession.set(false);
      },
    });
  }

  deactivateSession(token: string): void {
    if (!confirm('¿Desactivar esta sesión? El huésped perderá acceso al portal.')) return;
    this.api.deactivateSession(token, this.selectedPropId()).subscribe({
      next: () => {
        this.toast.success('Sesión desactivada');
        this.loadSessions();
      },
      error: (err) => this.toast.error(err?.error?.detail || 'Error al desactivar'),
    });
  }

  // ── Sidebar interactions ──

  selectConversation(roomLabel: string): void {
    this.selectedRoom.set(roomLabel);
    this.selectedRequest.set(null);
    this.messages.set([]);

    // Store booking_id for quick-request creation
    const conv = this.conversations().find((c) => c._id === roomLabel);
    this.selectedBookingId.set(conv?.booking_id ?? null);

    this.api.getConversationMessages(roomLabel, this.selectedPropId() ?? undefined).subscribe({
      next: (res) => this.messages.set(res.messages),
    });
  }

  selectRequest(req: ServiceRequest): void {
    this.selectedRequest.set(req);
    this.selectedRoom.set(null);
  }

  clearSelection(): void {
    this.selectedRoom.set(null);
    this.selectedRequest.set(null);
    this.messages.set([]);
  }

  setCategoryFilter(categoryId: string | null): void {
    this.requestCategoryFilter.set(categoryId);
  }

  setChatFilter(bucket: ChatBucket | null): void {
    this.chatFilter.set(bucket);
  }

  // ── Lost & Found ──

  private loadLostFound(): void {
    this.lostFoundLoading.set(true);
    const propId = this.selectedPropId();
    if (!propId) { this.lostFoundLoading.set(false); return; }
    const status = this.lostFoundStatusFilter() ?? undefined;
    const search = this.lostFoundSearch() || undefined;
    this.api.listLostFound({ prop_id: propId, status, search }).subscribe({
      next: (res) => {
        this.lostFoundItems.set((res.items ?? []) as unknown as LostItem[]);
        this.lostFoundLoading.set(false);
      },
      error: () => this.lostFoundLoading.set(false),
    });
  }

  createLostItem(): void {
    const propId = this.selectedPropId();
    const name = this.newLostItemName().trim();
    if (!propId || !name) { this.toast.warning('Nombre del objeto es requerido.'); return; }
    this.creatingLostItem.set(true);
    this.api.createLostItem({
      prop_id: propId,
      item_name: name,
      description: this.newLostDesc().trim(),
      found_location: this.newLostLocation().trim(),
      found_by: this.newLostFoundBy().trim(),
      booking_id: this.newLostBookingId().trim() || undefined,
      guest_name: this.newLostGuestName().trim() || undefined,
    }).subscribe({
      next: () => {
        this.toast.success('Objeto registrado');
        this.showLostFoundForm.set(false);
        this.newLostItemName.set('');
        this.newLostDesc.set('');
        this.newLostLocation.set('');
        this.newLostFoundBy.set('');
        this.newLostBookingId.set('');
        this.newLostGuestName.set('');
        this.creatingLostItem.set(false);
        this.loadLostFound();
      },
      error: (err) => {
        this.toast.error(err?.error?.detail || 'Error al crear');
        this.creatingLostItem.set(false);
      },
    });
  }

  claimLostItem(itemId: string, returnedTo = ''): void {
    if (!returnedTo) { this.toast.warning('Especifica a quién se entregó.'); return; }
    this.api.claimLostItem(itemId, returnedTo).subscribe({
      next: () => { this.toast.success('Objeto reclamado'); this.selectedLostItem.set(null); this.loadLostFound(); },
      error: (err) => this.toast.error(err?.error?.detail || 'Error al reclamar'),
    });
  }

  disposeLostItem(itemId: string): void {
    this.api.disposeLostItem(itemId).subscribe({
      next: () => { this.toast.success('Objeto desechado'); this.selectedLostItem.set(null); this.loadLostFound(); },
      error: (err) => this.toast.error(err?.error?.detail || 'Error al desechar'),
    });
  }

  openLostItemDetail(item: LostItem): void { this.selectedLostItem.set(item); }
  closeLostItemDetail(): void { this.selectedLostItem.set(null); }

  setLostStatusFilter(status: string | null): void {
    this.lostFoundStatusFilter.set(status);
    this.loadLostFound();
  }

  lostStatusLabel(status: string): string {
    const labels: Record<string, string> = { pending: 'Pendiente', found: 'Encontrado', claimed: 'Reclamado', disposed: 'Desechado', returned: 'Devuelto' };
    return labels[status] ?? status;
  }

  // ── Chat actions ──

  sendReply(): void {
    const room = this.selectedRoom();
    const msg = this.replyInput().trim();
    if (!room || !msg) return;

    this.sendingReply.set(true);
    this.api.staffReply(room, msg, this.selectedPropId()).subscribe({
      next: () => {
        this.replyInput.set('');
        this.sendingReply.set(false);
        this.selectConversation(room);
        this.loadData();
      },
      error: () => this.sendingReply.set(false),
    });
  }

  handleReplyKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendReply();
    }
  }

  // ── Confirm modal ──

  openConfirmModal(action: 'take' | 'complete' | 'cancel', req: ServiceRequest): void {
    const titles: Record<string, string> = {
      take: 'Tomar Solicitud',
      complete: 'Completar Solicitud',
      cancel: 'Cancelar Solicitud',
    };
    this.confirmActionType.set(action);
    this.confirmTarget.set(req);
    this.confirmTitle.set(titles[action]);
    this.confirmMessage.set(`${req.request_type_label} — Hab. ${req.room_label}`);
    this.staffResponseInput.set('');
    this.newCheckOutDate.set('');
    this.showConfirmModal.set(true);
  }

  closeConfirmModal(): void {
    this.showConfirmModal.set(false);
    this.confirmActionType.set(null);
    this.confirmTarget.set(null);
  }

  confirmAction(): void {
    const action = this.confirmActionType();
    const req = this.confirmTarget();
    if (!action || !req) return;

    const statusMap: Record<string, string> = {
      take: 'in_progress',
      complete: 'completed',
      cancel: 'cancelled',
    };
    const newStatus = statusMap[action];
    const response = this.staffResponseInput().trim();
    const newDate = action === 'complete' && req.request_type === 'extend_stay'
      ? this.newCheckOutDate()
      : undefined;

    this.api.updateRequest(req._id, newStatus, response, newDate).subscribe({
      next: () => {
        this.closeConfirmModal();
        const propId = this.selectedPropId() ?? undefined;
        this.api.listRequests(propId, undefined).subscribe({
          next: (res) => this.requests.set(res.items),
        });

        if (this.selectedRequest()?._id === req._id) {
          this.selectedRequest.set({
            ...req,
            status: newStatus as ServiceRequest['status'],
            staff_response: response || req.staff_response,
          });
        }
      },
    });
  }

  // ── Request actions ──

  dndFor(roomLabel: string): boolean {
    return this.conversationsMap()[roomLabel]?.dnd ?? false;
  }

  quickCreateRequest(categoryId: string): void {
    const bookingId = this.selectedBookingId();
    if (!bookingId) {
      this.toast.warning('Selecciona una conversación primero.');
      return;
    }
    const cat = this.categories.find((c) => c.id === categoryId);
    const label = cat?.label ?? categoryId;

    this.api.staffCreateRequest(bookingId, categoryId, `Solicitud de ${label}`).subscribe({
      next: () => {
        this.toast.success(`Solicitud de ${label} creada`);
        const propId = this.selectedPropId() ?? undefined;
        this.api.listRequests(propId, undefined).subscribe({
          next: (res) => this.requests.set(res.items),
        });
      },
      error: (err) => {
        this.toast.error(err?.error?.detail || 'Error al crear la solicitud');
      },
    });
  }

  // ── Property selector ──

  onPropSelected(event: { propId: number; label: string }): void {
    const label = event.label || `Propiedad #${event.propId}`;
    this.selectedLabel.set(label);

    if (event.propId) {
      this.propCtx.setProperty(event.propId, label);
    } else {
      this.propCtx.clear();
    }

    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: event.propId || null },
      queryParamsHandling: 'merge',
    });

    this.loadData();
    this.connectSse();
  }

  // ── SSE Notifications ──

  private connectSse(): void {
    this.sseSub?.unsubscribe();
    const propId = this.selectedPropId();
    if (!propId) return;

    this.sseSub = this.sse.connect(propId).subscribe({
      next: (notification) => {
        if (notification.type === 'new_message') {
          this.toast.info(`Nuevo mensaje de ${notification.data.guest_name} (Hab. ${notification.data.room_label})`);
        } else if (notification.type === 'new_request') {
          this.toast.warning(`Nueva solicitud: ${notification.data.request_type || 'Servicio'} (Hab. ${notification.data.room_label})`);
        } else if (notification.type === 'lost_found_create') {
          this.toast.info(`Objeto perdido registrado: ${notification.data.item_name || 'Sin nombre'}`);
          if (this.activeTab() === 'lost-found') this.loadLostFound();
        } else if (notification.type === 'lost_found_claim') {
          this.toast.success(`Objeto reclamado: ${notification.data.item_name || 'Sin nombre'}`);
          if (this.activeTab() === 'lost-found') this.loadLostFound();
        } else if (notification.type === 'lost_found_dispose') {
          this.toast.info(`Objeto desechado: ${notification.data.item_name || 'Sin nombre'}`);
          if (this.activeTab() === 'lost-found') this.loadLostFound();
        } else if (notification.type === 'request_updated') {
          const newStatus = notification.data.status_label || notification.data.new_status || '';
          this.toast.success(`Solicitud ${notification.data.request_type || ''} → ${newStatus} (Hab. ${notification.data.room_label})`);
          // If we're viewing this specific request, update it locally
          const selected = this.selectedRequest();
          if (selected && selected._id === notification.data.request_id) {
            this.selectedRequest.set({
              ...selected,
              status: (notification.data.new_status || selected.status) as ServiceRequest['status'],
              status_label: notification.data.status_label || selected.status_label,
            });
          }
        } else if (notification.type === 'dnd_toggled') {
          const dndOn = notification.data.dnd_active;
          const room = notification.data.room_label || '';
          const guest = notification.data.guest_name || 'Huésped';
          const action = dndOn ? 'activó' : 'desactivó';
          this.toast.info(`${guest} (Hab. ${room}) ${action} No Molestar`);
          // Update conversation locally so DND badge reflects immediately
          const convs = this.conversations();
          const idx = convs.findIndex((c) => c._id === room);
          if (idx >= 0) {
            const updated = [...convs];
            updated[idx] = { ...updated[idx], dnd: !!dndOn };
            this.conversations.set(updated);
          }
        }
        // Auto-refresh data (lightweight — no loading flag)
        this.refreshData();
      },
    });
  }

  private refreshData(): void {
    const propId = this.selectedPropId();
    if (!propId) return;
    this.api.listConversations(propId).subscribe({
      next: (res) => this.conversations.set(res.conversations),
    });
    this.api.listRequests(propId, undefined).subscribe({
      next: (res) => this.requests.set(res.items),
    });
  }

  // ── Folio modals ──

  openPaymentModal(folio: LedgerFolio): void {
    this.paymentModalError.set('');
    this.paymentModalFolio.set(folio);
  }

  openTransferModal(folio: LedgerFolio): void {
    this.paymentModalError.set('');
    this.transferModalFolio.set(folio);
  }

  closePaymentModal(): void {
    this.paymentModalFolio.set(null);
    this.paymentModalError.set('');
  }

  closeTransferModal(): void {
    this.transferModalFolio.set(null);
    this.paymentModalError.set('');
  }

  closeTransactionsModal(): void {
    this.transactionsModalFolio.set(null);
  }

  openTransactionsModal(folio: LedgerFolio): void {
    this.transactionsModalFolio.set(folio);
  }

  onPaymentConfirmed(event: { amount: number; method?: string; notes: string }): void {
    const folio = this.paymentModalFolio();
    if (!folio) return;

    this.ledgerApi.postFolioPayment(
      folio.folioId,
      event.amount,
      event.method ?? 'cash',
      event.notes,
      this.selectedPropId(),
    ).subscribe({
      next: () => {
        this.toast.success(`Pago de ${formatCurrency(event.amount, 'en-US', '$', 'USD', '1.0-2')} registrado`);
        this.closePaymentModal();
        this.loadFolios();
      },
      error: (err) => {
        this.paymentModalError.set(err?.error?.detail || 'Error al registrar el pago');
      },
    });
  }

  onTransferConfirmed(event: { amount: number; notes: string; targetFolioId?: string }): void {
    const folio = this.transferModalFolio();
    if (!folio || !event.targetFolioId) return;

    this.ledgerApi.transferFolioCharges(
      folio.folioId,
      event.targetFolioId,
      event.amount,
      event.notes,
      this.selectedPropId(),
    ).subscribe({
      next: () => {
        this.toast.success(`Transferencia de ${formatCurrency(event.amount, 'en-US', '$', 'USD', '1.0-2')} completada`);
        this.closeTransferModal();
        this.loadFolios();
      },
      error: (err) => {
        this.paymentModalError.set(err?.error?.detail || 'Error al transferir cargos');
      },
    });
  }

  // ── Icon helper exposed to template ──
  protected readonly getRequestIcon = getRequestIcon;
}
