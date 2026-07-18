import { ChangeDetectionStrategy, Component, computed, inject, OnInit, signal, ViewEncapsulation } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { ActivatedRoute } from '@angular/router';

import { InStayApiService } from '../../services/in-stay-api.service';
import { PortalData, ChatMessage, ServiceRequest } from '../../models/in-stay.model';
import { GpConfirmModalComponent } from './components/gp-confirm-modal.component';
import { GpPaymentModalComponent } from './components/gp-payment-modal.component';

interface GuestNotification {
  id: string;
  type: 'staff_message' | 'request_update' | 'request_response';
  icon: string;
  title: string;
  body: string;
  created_at: string;
  read: boolean;
}

type Tab = 'compendium' | 'services' | 'chat' | 'charges';

@Component({
  selector: 'app-guest-portal',
  imports: [FormsModule, CurrencyPipe, DatePipe, GpConfirmModalComponent, GpPaymentModalComponent],
  templateUrl: './guest-portal-page.html',
  styleUrl: './guest-portal-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
})
export class GuestPortalPageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(InStayApiService);

  // ── State ──
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly portalData = signal<PortalData | null>(null);
  readonly activeTab = signal<Tab>('compendium');
  readonly dndActive = signal(false);
  readonly dndToggling = signal(false);

  // Chat
  readonly messages = signal<ChatMessage[]>([]);
  readonly chatInput = signal('');
  readonly sendingChat = signal(false);

  // Service requests
  readonly requests = signal<ServiceRequest[]>([]);
  readonly requestType = signal('other');
  readonly requestDesc = signal('');
  readonly sendingRequest = signal(false);
  readonly requestDone = signal(false);
  readonly quickRequestSuccess = signal('');

  readonly requestTypes: { value: string; label: string }[] = [
    { value: 'housekeeping', label: 'Limpieza' },
    { value: 'towels', label: 'Toallas adicionales' },
    { value: 'amenities', label: 'Amenities' },
    { value: 'maintenance', label: 'Mantenimiento' },
    { value: 'room_service', label: 'Servicio a la habitación' },
    { value: 'minibar', label: 'Minibar' },
    { value: 'laundry', label: 'Lavandería' },
    { value: 'wake_up_call', label: 'Llamada de despertar' },
    { value: 'late_checkout', label: 'Late check-out' },
    { value: 'extra_bed', label: 'Cama adicional' },
    { value: 'spa', label: 'Spa & Bienestar' },
    { value: 'restaurant', label: 'Reserva en restaurante' },
    { value: 'extend_stay', label: 'Extender estancia' },
    { value: 'other', label: 'Otro' },
  ];

  /** Tabs reactivas derivadas de portalData */
  readonly tabs = computed<{ id: Tab; icon: string; label: string; badge?: number }[]>(() => {
    const data = this.portalData();
    if (!data) return [];
    return [
      { id: 'compendium', icon: 'info', label: 'Hotel' },
      { id: 'services', icon: 'concierge', label: 'Servicios', badge: data.pending_requests },
      { id: 'chat', icon: 'chat', label: 'Chat', badge: data.unread_messages },
      { id: 'charges', icon: 'receipt_long', label: 'Cargos' },
    ];
  });

  /** Computed: folio postings sorted by date desc */
  readonly recentPostings = computed(() => {
    const data = this.portalData();
    if (!data?.folio_postings) return [];
    return [...data.folio_postings].sort((a, b) => b.posted_at.localeCompare(a.posted_at));
  });

  /** Hotel amenities from DB — purely informational display. */
  readonly hotelAmenities = computed(() => {
    const data = this.portalData();
    return data?.compendium?.amenities ?? [];
  });

  /** Requests sorted: pending/in-progress first, completed/cancelled last. */
  readonly sortedRequests = computed(() => {
    const reqs = this.requests();
    const active: ServiceRequest[] = [];
    const resolved: ServiceRequest[] = [];
    for (const r of reqs) {
      if (r.status === 'pending' || r.status === 'in_progress') {
        active.push(r);
      } else {
        resolved.push(r);
      }
    }
    // Most recent first within each group
    active.sort((a, b) => b.created_at.localeCompare(a.created_at));
    resolved.sort((a, b) => b.created_at.localeCompare(a.created_at));
    return [...active, ...resolved];
  });

  /** Number of requests to show initially (expandable). */
  readonly requestDisplayLimit = signal(5);

  /** Requests visible based on current limit. */
  readonly visibleRequests = computed(() => this.sortedRequests().slice(0, this.requestDisplayLimit()));

  readonly hasMoreRequests = computed(() => this.sortedRequests().length > this.requestDisplayLimit());

  showMoreRequests(): void {
    this.requestDisplayLimit.update((n) => n + 5);
  }

  // ── Notifications ──

  readonly showNotifications = signal(false);
  private readonly readNotificationIds = signal<Set<string>>(new Set());

  /** Computed: derive guest notifications from chat + requests data. */
  readonly guestNotifications = computed<GuestNotification[]>(() => {
    const msgs = this.messages();
    const reqs = this.requests();
    const results: GuestNotification[] = [];

    // Staff messages
    for (const m of msgs) {
      if (m.sender === 'staff') {
        results.push({
          id: `msg-${m._id}`,
          type: 'staff_message',
          icon: 'chat',
          title: m.staff_name ? `Mensaje de ${m.staff_name}` : 'Mensaje de Recepción',
          body: m.message,
          created_at: m.created_at,
          read: m.read || this.readNotificationIds().has(`msg-${m._id}`),
        });
      }
    }

    // Request updates & responses
    for (const r of reqs) {
      if (r.status !== 'pending') {
        results.push({
          id: `req-status-${r._id}`,
          type: 'request_update',
          icon: 'task_alt',
          title: `${r.request_type_label || 'Solicitud'} — ${r.status_label}`,
          body: r.description || `Tu solicitud fue actualizada a "${r.status_label}".`,
          created_at: r.resolved_at || r.created_at,
          read: this.readNotificationIds().has(`req-status-${r._id}`),
        });
      }
      if (r.staff_response) {
        results.push({
          id: `req-resp-${r._id}`,
          type: 'request_response',
          icon: 'reply',
          title: `Respuesta a "${r.request_type_label || 'tu solicitud'}"`,
          body: r.staff_response,
          created_at: r.resolved_at || r.created_at,
          read: this.readNotificationIds().has(`req-resp-${r._id}`),
        });
      }
    }

    results.sort((a, b) => b.created_at.localeCompare(a.created_at));
    return results.slice(0, 50);
  });

  readonly unreadNotificationCount = computed(() =>
    this.guestNotifications().filter((n) => !n.read).length
  );

  toggleNotifications(): void {
    this.showNotifications.update((v) => !v);
  }

  closeNotifications(): void {
    this.showNotifications.set(false);
  }

  markAllNotificationsRead(): void {
    const ids = new Set(this.guestNotifications().map((n) => n.id));
    this.readNotificationIds.set(ids);
  }

  goBack(): void {
    history.back();
  }

  private tokenValue = '';

  ngOnInit(): void {
    this.route.paramMap.subscribe((params) => {
      const tok = params.get('token') ?? '';
      if (tok) {
        this.tokenValue = tok;
        this.loadPortal(tok);
      } else {
        this.error.set('Token no encontrado en la URL.');
        this.loading.set(false);
      }
    });
  }

  private loadPortal(token: string): void {
    this.loading.set(true);
    this.error.set(null);

    this.api.getPortalData(token).subscribe({
      next: (data) => {
        this.portalData.set(data);
        this.dndActive.set(data.dnd_active);
        this.loading.set(false);

        // Preload chat, requests and lost items
        this.loadMessages();
        this.loadRequests();
        this.loadLostItems();
        // Initialize read state — mark all existing notifications as read so only future ones count as unread
        setTimeout(() => this.markAllNotificationsRead(), 500);
      },
      error: (err) => {
        this.loading.set(false);
        if (err.status === 404 || err.status === 410) {
          this.error.set('El enlace ha expirado o no es válido. Contacta a recepción.');
        } else {
          this.error.set('Error al cargar el portal. Intenta de nuevo.');
        }
      },
    });
  }

  // ── DND Toggle ──

  toggleDnd(): void {
    if (this.dndToggling() || !this.tokenValue) return;
    const newValue = !this.dndActive();
    this.dndActive.set(newValue);
    this.dndToggling.set(true);
    this.api.toggleDnd(this.tokenValue).subscribe({
      next: (res) => {
        this.dndActive.set(res.dnd_active);
        this.dndToggling.set(false);
      },
      error: () => {
        this.dndActive.set(!newValue);
        this.dndToggling.set(false);
      },
    });
  }

  // ── Tabs ──

  setTab(tab: Tab): void {
    this.activeTab.set(tab);
    if (tab === 'chat') this.loadMessages();
    if (tab === 'services') this.loadRequests();
  }

  /** Unified navigation — scrolls to section on desktop, switches tab on mobile. */
  navToTab(tab: Tab): void {
    this.setTab(tab);
    // On desktop, scroll bento section into view
    if (window.innerWidth >= 768) {
      const el = document.getElementById(`gp-section-${tab}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }
  }

  // ── Chat ──

  private loadMessages(): void {
    if (!this.tokenValue) return;
    this.api.getChatMessages(this.tokenValue).subscribe({
      next: (res) => this.messages.set(res.messages),
    });
  }

  sendMessage(): void {
    const msg = this.chatInput().trim();
    if (!msg || !this.tokenValue) return;

    this.sendingChat.set(true);
    this.api.sendMessage(this.tokenValue, msg).subscribe({
      next: () => {
        this.chatInput.set('');
        this.sendingChat.set(false);
        this.loadMessages();
      },
      error: () => (this.sendingChat.set(false)),
    });
  }

  // ── Lost & Found ──

  readonly lostItems = signal<{_id: string; description: string; status: string; location_found: string; reported_by: string; returned_to: string; created_at: string}[]>([]);

  private loadLostItems(): void {
    if (!this.tokenValue) return;
    this.api.getLostItems(this.tokenValue).subscribe({
      next: (res) => this.lostItems.set(res.items),
    });
  }

  lostStatusLabel(status: string): string {
    const labels: Record<string, string> = { found: 'Encontrado', claimed: 'Reclamado', disposed: 'Desechado' };
    return labels[status] || status;
  }

  // ── Service Requests ──

  private loadRequests(): void {
    if (!this.tokenValue) return;
    this.requestDisplayLimit.set(5);
    this.api.getRequests(this.tokenValue).subscribe({
      next: (res) => this.requests.set(res.items),
    });
  }

  submitRequest(): void {
    if (!this.requestDesc().trim() || !this.tokenValue) return;
    this.sendServiceRequest(this.requestType(), this.requestDesc().trim());
  }

  private sendServiceRequest(type: string, desc: string): void {
    if (!this.tokenValue) return;
    this.sendingRequest.set(true);
    this.showConfirmModal.set(false);
    this.quickRequestSuccess.set('');
    this.api
      .createRequest(this.tokenValue, type, desc)
      .subscribe({
        next: (res: any) => {
          this.sendingRequest.set(false);
          this.requestDone.set(true);
          this.requestDesc.set('');
          // Auto-update DND if it was deactivated by the request
          if (res?.dnd_was_active) {
            this.dndActive.set(false);
          }
          const label = this.requestTypes.find((r) => r.value === type)?.label || 'Solicitud';
          this.quickRequestSuccess.set(`${label} enviada. Recepción te atenderá pronto.`);
          setTimeout(() => { this.quickRequestSuccess.set(''); this.requestDone.set(false); }, 4000);
          this.loadRequests();
        },
        error: () => {
          this.sendingRequest.set(false);
          this.quickRequestSuccess.set('Error al enviar la solicitud. Intenta de nuevo.');
          setTimeout(() => this.quickRequestSuccess.set(''), 5000);
        },
      });
  }

  cancelRequest(requestId: string): void {
    if (!this.tokenValue) return;
    this.api.cancelRequest(this.tokenValue, requestId).subscribe({
      next: () => {
        this.quickRequestSuccess.set('Solicitud cancelada.');
        setTimeout(() => this.quickRequestSuccess.set(''), 3000);
        this.loadRequests();
      },
      error: () => {
        this.quickRequestSuccess.set('Error al cancelar la solicitud.');
        setTimeout(() => this.quickRequestSuccess.set(''), 3000);
      },
    });
  }

  // ── Confirmation Modal ──

  readonly showConfirmModal = signal(false);
  readonly confirmTitle = signal('');
  readonly confirmMessage = signal('');
  readonly confirmActionType = signal('');
  readonly confirmActionDesc = signal('');

  openConfirmModal(type: string, label: string): void {
    this.confirmTitle.set(`¿Confirmar ${label}?`);
    this.confirmMessage.set(`Se enviará una solicitud de "${label}" a recepción. ¿Deseas continuar?`);
    this.confirmActionType.set(type);
    this.confirmActionDesc.set('');
    this.showConfirmModal.set(true);
  }

  confirmAction(): void {
    let desc = this.confirmActionDesc();
    const type = this.confirmActionType();
    if (this.showExtendFields()) {
      const date = this.extendDate();
      const time = this.extendTime();
      if (type === 'extend_stay' && !date) return;
      if (type === 'late_checkout' && !time) return;
      desc = type === 'extend_stay'
        ? `Solicito extender mi estancia hasta: ${date}`
        : `Solicito late check-out a las: ${time}`;
    }
    this.sendServiceRequest(type, desc);
  }

  // ── Extend Stay / Late Checkout Modal ──

  readonly showExtendFields = computed(() => {
    const t = this.confirmActionType();
    return t === 'extend_stay' || t === 'late_checkout';
  });

  readonly extendDate = signal('');
  readonly extendTime = signal('');

  // ── Payment Modal ──

  readonly showPaymentModal = signal(false);
  readonly paymentModalMode = signal<'invoice' | 'payment'>('payment');

  requestInvoice(): void {
    this.paymentModalMode.set('invoice');
    this.showPaymentModal.set(true);
  }

  requestPayment(): void {
    this.paymentModalMode.set('payment');
    this.showPaymentModal.set(true);
  }

  closePaymentModal(): void {
    this.showPaymentModal.set(false);
  }

  confirmPaymentRequest(): void {
    // Notify staff via a service request
    const mode = this.paymentModalMode();
    const type = mode === 'invoice' ? 'solicitar_factura' : 'solicitar_pago';
    const desc = mode === 'invoice'
      ? 'Solicito la factura de mi estancia para revisión.'
      : 'Solicito realizar un pago en mi folio. Por favor contactarme.';

    this.sendingRequest.set(true);
    this.api.createRequest(this.tokenValue, type, desc).subscribe({
      next: (res: any) => {
        this.sendingRequest.set(false);
        if (res?.dnd_was_active) {
          this.dndActive.set(false);
        }
        this.showPaymentModal.set(false);
        this.loadRequests();
      },
      error: () => this.sendingRequest.set(false),
    });
  }

  // ── Helpers ──

  getChargesTotal(): number {
    const data = this.portalData();
    if (!data) return 0;
    return data.charges.reduce((sum, c) => sum + c.total, 0);
  }

  getFolioTotal(): number {
    return this.portalData()?.folio_balance ?? 0;
  }

  isToday(dateStr: string): boolean {
    const today = new Date().toISOString().slice(0, 10);
    return dateStr.slice(0, 10) === today;
  }

}
