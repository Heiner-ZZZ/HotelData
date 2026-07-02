import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { DatePipe, CurrencyPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { InStayApiService } from '../../services/in-stay-api.service';
import { Conversation, ChatMessage, ServiceRequest } from '../../models/in-stay.model';

type StaffTab = 'chat' | 'requests';

@Component({
  selector: 'app-staff-inbox',
  imports: [DatePipe, CurrencyPipe, FormsModule, PropertySelectorComponent],
  templateUrl: './staff-inbox-page.html',
  styleUrl: './staff-inbox-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StaffInboxPageComponent {
  private readonly api = inject(InStayApiService);
  private readonly propCtx = inject(PropertyContextService);
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
}
