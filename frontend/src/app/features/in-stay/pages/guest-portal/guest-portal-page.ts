import { ChangeDetectionStrategy, Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { ActivatedRoute } from '@angular/router';

import { InStayApiService } from '../../services/in-stay-api.service';
import { PortalData, ChatMessage, ServiceRequest } from '../../models/in-stay.model';

type Tab = 'compendium' | 'services' | 'chat' | 'charges';

@Component({
  selector: 'app-guest-portal',
  imports: [FormsModule, CurrencyPipe, DatePipe],
  templateUrl: './guest-portal-page.html',
  styleUrl: './guest-portal-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GuestPortalPageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(InStayApiService);

  // ── State ──
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly portalData = signal<PortalData | null>(null);
  readonly activeTab = signal<Tab>('compendium');

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
        this.loading.set(false);

        // tabs se actualiza automáticamente via computed()

        // Preload chat and requests
        this.loadMessages();
        this.loadRequests();
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

  // ── Tabs ──

  setTab(tab: Tab): void {
    this.activeTab.set(tab);
    if (tab === 'chat') this.loadMessages();
    if (tab === 'services') this.loadRequests();
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

  // ── Service Requests ──

  private loadRequests(): void {
    if (!this.tokenValue) return;
    this.api.getRequests(this.tokenValue).subscribe({
      next: (res) => this.requests.set(res.items),
    });
  }

  submitRequest(): void {
    if (!this.requestDesc().trim() || !this.tokenValue) return;

    this.sendingRequest.set(true);
    this.api
      .createRequest(this.tokenValue, this.requestType(), this.requestDesc().trim())
      .subscribe({
        next: () => {
          this.requestDone.set(true);
          this.sendingRequest.set(false);
          this.requestDesc.set('');
          setTimeout(() => this.requestDone.set(false), 3000);
          this.loadRequests();
        },
        error: () => (this.sendingRequest.set(false)),
      });
  }

  // ── Helpers ──

  getChargesTotal(): number {
    const data = this.portalData();
    if (!data) return 0;
    return data.charges.reduce((sum, c) => sum + c.total, 0);
  }

  isToday(dateStr: string): boolean {
    const today = new Date().toISOString().slice(0, 10);
    return dateStr.slice(0, 10) === today;
  }
}
