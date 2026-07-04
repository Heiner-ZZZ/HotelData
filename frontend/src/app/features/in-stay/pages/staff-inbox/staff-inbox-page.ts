import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
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

type StaffTab = 'chat' | 'requests' | 'folios';

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

  readonly activeTab = signal<StaffTab>('chat');
  readonly loading = signal(true);
  readonly conversations = signal<Conversation[]>([]);
  readonly requests = signal<ServiceRequest[]>([]);
  readonly selectedRoom = signal<string | null>(null);
  readonly messages = signal<ChatMessage[]>([]);
  readonly replyInput = signal('');
  readonly sendingReply = signal(false);
  readonly requestFilter = signal<string>('pending');
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

  private loadData(): void {
    this.loading.set(true);
    const propId = this.selectedPropId() ?? undefined;
    this.api.listConversations(propId).subscribe({
      next: (res) => {
        this.conversations.set(res.conversations);
        this.loading.set(false);
      },
      error: () => (this.loading.set(false)),
    });
    this.loadRequests(propId);
    this.loadFolios();
  }

  private loadRequests(propId?: number): void {
    this.api.listRequests(propId, this.requestFilter()).subscribe({
      next: (res) => this.requests.set(res.items),
    });
  }

  setTab(tab: StaffTab): void {
    this.activeTab.set(tab);
    if (tab === 'requests') {
      this.loadRequests(this.selectedPropId() ?? undefined);
    }
    if (tab === 'folios') {
      this.loadFolios();
    }
  }

  // ─── Folio Transactions Modal ───

  openTransactionsModal(folio: LedgerFolio): void {
    this.transactionsModalFolio.set(folio);
  }

  closeTransactionsModal(): void {
    this.transactionsModalFolio.set(null);
  }

  filterRequests(status: string): void {
    this.requestFilter.set(status);
    this.loadRequests(this.selectedPropId() ?? undefined);
  }

  selectConversation(roomLabel: string): void {
    this.selectedRoom.set(roomLabel);
    this.messages.set([]);
    this.api.getConversationMessages(roomLabel, this.selectedPropId() ?? undefined).subscribe({
      next: (res) => this.messages.set(res.messages),
    });
  }

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
        this.loadData(); // refresh conversations list
      },
      error: () => (this.sendingReply.set(false)),
    });
  }

  updateRequest(req: ServiceRequest, status: string): void {
    this.api.updateRequest(req._id, status, '').subscribe({
      next: () => this.loadRequests(this.selectedPropId() ?? undefined),
    });
  }

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

  backToConversations(): void {
    this.selectedRoom.set(null);
  }

  getUnreadCount(): number {
    return this.conversations().reduce((sum, c) => sum + c.unread, 0);
  }

  get pendingCount(): number {
    return this.requests().filter((r) => r.status === 'pending' || r.status === 'in_progress').length;
  }

  get folioCount(): number {
    return this.folios().length;
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

  // ─── Folio Payment Modal ───

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
