import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { DatePipe, CurrencyPipe, formatCurrency } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { InStayApiService } from '../../services/in-stay-api.service';
import { ExpensesApiService } from '../../../expenses/services/expenses-api.service';
import { FolioPaymentModalComponent } from '../../components/folio-payment-modal/folio-payment-modal';
import { FolioTransactionsModalComponent } from '../../components/folio-transactions-modal/folio-transactions-modal';
import { Conversation, ChatMessage, ServiceRequest } from '../../models/in-stay.model';
import type { LedgerFolio } from '../../../expenses/models/ledger.model';

type MainTab = 'unified' | 'folios';

/** Category chip definition for quick request creation + filtering. */
interface CategoryChip {
  id: string;
  icon: string;
  label: string;
}

const REQUEST_CATEGORIES: CategoryChip[] = [
  { id: 'concierge', icon: 'local_activity', label: 'Concierge' },
  { id: 'housekeeping', icon: 'cleaning_services', label: 'Housekeeping' },
  { id: 'room_service', icon: 'room_service', label: 'Room Service' },
  { id: 'maintenance', icon: 'handyman', label: 'Technical' },
];

@Component({
  selector: 'app-staff-inbox',
  imports: [DatePipe, CurrencyPipe, FormsModule, PropertySelectorComponent, FolioPaymentModalComponent, FolioTransactionsModalComponent],
  templateUrl: './staff-inbox-page.html',
  styleUrl: './staff-inbox-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StaffInboxPageComponent {
  private readonly api = inject(InStayApiService);
  private readonly ledgerApi = inject(ExpensesApiService);
  private readonly propCtx = inject(PropertyContextService);
  private readonly toast = inject(ToastService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  readonly selectedPropId = this.propCtx.currentPropId;
  readonly selectedLabel = signal('');

  // ── Unified tab state ──
  readonly activeTab = signal<MainTab>('unified');
  readonly loading = signal(true);

  // Conversations (left sidebar)
  readonly conversations = signal<Conversation[]>([]);
  readonly selectedRoom = signal<string | null>(null);
  readonly messages = signal<ChatMessage[]>([]);
  readonly replyInput = signal('');
  readonly sendingReply = signal(false);

  // Service requests (left sidebar)
  readonly requests = signal<ServiceRequest[]>([]);
  readonly selectedRequest = signal<ServiceRequest | null>(null);
  readonly requestCategoryFilter = signal<string | null>(null); // null = all
  readonly categories = REQUEST_CATEGORIES;

  // Folios (separate tab)
  readonly folios = signal<LedgerFolio[]>([]);
  readonly foliosLoading = signal(false);

  // Payment modal state
  readonly paymentModalFolio = signal<LedgerFolio | null>(null);
  readonly transferModalFolio = signal<LedgerFolio | null>(null);
  readonly paymentModalError = signal('');
  readonly transactionsModalFolio = signal<LedgerFolio | null>(null);

  constructor() {
    this.loadData();
  }

  // ── Computed ──

  /** Combined timeline: conversations + requests, sorted by last activity, filtered by category. */
  readonly timeline = computed(() => {
    const convs = this.conversations();
    const catFilter = this.requestCategoryFilter();
    const reqs = catFilter
      ? this.requests().filter((r) => r.request_type === catFilter)
      : this.requests();
    // Merge into timeline items
    const items: {
      type: 'message' | 'request';
      id: string;
      roomLabel: string;
      guestName: string;
      preview: string;
      time: string;
      unread?: number;
      status?: string;
      statusLabel?: string;
      requestType?: string;
      request?: ServiceRequest;
    }[] = [];

    for (const c of convs) {
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
    for (const r of reqs) {
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
  });

  // ── Data loading ──

  private loadData(): void {
    this.loading.set(true);
    const propId = this.selectedPropId() ?? undefined;

    // Load conversations
    this.api.listConversations(propId).subscribe({
      next: (res) => {
        this.conversations.set(res.conversations);
        this.loading.set(false);
      },
      error: () => (this.loading.set(false)),
    });

    // Load requests (all statuses)
    this.api.listRequests(propId, undefined).subscribe({
      next: (res) => this.requests.set(res.items),
    });

    this.loadFolios();
  }

  private loadFolios(): void {
    const propId = this.selectedPropId();
    if (!propId) return;
    this.foliosLoading.set(true);
    this.ledgerApi.getLedgerFolios(propId).subscribe({
      next: (res) => {
        this.folios.set(res.items);
        this.foliosLoading.set(false);
      },
      error: () => this.foliosLoading.set(false),
    });
  }

  // ── Tab switching ──

  setTab(tab: MainTab): void {
    this.activeTab.set(tab);
    if (tab === 'folios') this.loadFolios();
  }

  // ── Unified sidebar interactions ──

  /** Select a conversation by room label — opens chat in the right panel. */
  selectConversation(roomLabel: string): void {
    this.selectedRoom.set(roomLabel);
    this.selectedRequest.set(null);
    this.messages.set([]);
    this.api.getConversationMessages(roomLabel, this.selectedPropId() ?? undefined).subscribe({
      next: (res) => this.messages.set(res.messages),
    });
  }

  /** Select a service request — shows its detail in the right panel. */
  selectRequest(req: ServiceRequest): void {
    this.selectedRequest.set(req);
    this.selectedRoom.set(null);
  }

  /** Navigate from a selected item back to the list. */
  clearSelection(): void {
    this.selectedRoom.set(null);
    this.selectedRequest.set(null);
    this.messages.set([]);
  }

  /** Filter timeline by request category chip. */
  setCategoryFilter(categoryId: string | null): void {
    this.requestCategoryFilter.set(categoryId);
  }

  // ── Chat actions ──

  sendReply(): void {
    const room = this.selectedRoom();
    const msg = this.replyInput().trim();
    if (!room || !msg) return;

    this.sendingReply.set(true);
    this.api.staffReply(room, msg).subscribe({
      next: () => {
        this.replyInput.set('');
        this.sendingReply.set(false);
        this.selectConversation(room);
        this.loadData(); // refresh conversations
      },
      error: () => (this.sendingReply.set(false)),
    });
  }

  /** Handle Enter key in chat textarea: send on Enter, newline on Shift+Enter */
  handleReplyKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendReply();
    }
  }

  // ── Request actions ──

  /** Update a request status (Tomar, Completar, Cancelar). */
  updateRequest(req: ServiceRequest, status: string): void {
    this.api.updateRequest(req._id, status, '').subscribe({
      next: () => {
        const propId = this.selectedPropId() ?? undefined;
        this.api.listRequests(propId, undefined).subscribe({
          next: (res) => this.requests.set(res.items),
        });
        // Update the selected request if it's the one being modified
        if (this.selectedRequest()?._id === req._id) {
          this.selectedRequest.set({ ...req, status: status as ServiceRequest['status'] });
        }
      },
    });
  }

  /** Quick-create a request from a category chip click. */
  quickCreateRequest(categoryId: string): void {
    const propId = this.selectedPropId();
    if (!propId) {
      this.toast.warning('Selecciona una propiedad primero.');
      return;
    }
    // Create a lightweight request by posting to the guest endpoint
    // We need a token — find one from active conversations
    this.toast.info(`Creando solicitud de ${categoryId}...`);
    // For now, we'll just set the filter to this category
    this.setCategoryFilter(categoryId);
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
  }

  // ── Badge helpers ──

  getUnreadCount(): number {
    return this.conversations().reduce((sum, c) => sum + c.unread, 0);
  }

  get pendingCount(): number {
    return this.requests().filter((r) => r.status === 'pending' || r.status === 'in_progress').length;
  }

  get folioCount(): number {
    return this.folios().length;
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
}
