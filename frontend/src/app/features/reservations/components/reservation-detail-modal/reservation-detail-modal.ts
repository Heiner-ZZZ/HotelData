import { ChangeDetectionStrategy, Component, effect, ElementRef, HostListener, input, output, ViewChild } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { CdkTrapFocus } from '@angular/cdk/a11y';
import type { ReceptionCalendarReservation } from '../../models/reception-calendar.model';
import type { ReservationDetailDto } from '../../models/reservations.dto';
import type { ReservationDetailViewModel } from '../../models/reservations.model';
import { mapReservationDetail } from '../../mappers/reservations.mapper';

@Component({
  selector: 'app-reservation-detail-modal',
  imports: [CdkTrapFocus, DecimalPipe, RouterLink],
  templateUrl: './reservation-detail-modal.html',
  styleUrl: './reservation-detail-modal.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReservationDetailModalComponent {
  readonly reservation = input.required<ReceptionCalendarReservation>();
  readonly presentation = input<'modal' | 'side-panel'>('modal');
  readonly closed = output<void>();

  readonly detailResource = httpResource<ReservationDetailViewModel>(() => {
    const bookingId = this.reservation().bookingId;
    return bookingId ? `/reservations/${bookingId}` : undefined;
  }, {
    parse: (dto) => mapReservationDetail(dto as ReservationDetailDto),
  });

  @ViewChild('closeButton', { static: false })
  readonly closeButton?: ElementRef<HTMLButtonElement>;

  private previousActiveElement: HTMLElement | null = null;

  constructor() {
    effect(() => {
      const bookingId = this.reservation().bookingId;
      if (bookingId) {
        if (!this.previousActiveElement) {
          this.previousActiveElement = document.activeElement instanceof HTMLElement
            ? document.activeElement
            : null;
        }
        queueMicrotask(() => this.closeButton?.nativeElement?.focus());
      }
    });
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.close();
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (this.presentation() !== 'side-panel') return;
    const target = event.target;
    if (!(target instanceof Node)) return;
    if (this.closeButton?.nativeElement.closest('.reservation-detail-dialog')?.contains(target)) return;
    if (target instanceof Element && target.closest('.hotel-timeline-schedule')) return;
    this.close();
  }

  close(): void {
    this.previousActiveElement?.focus();
    this.previousActiveElement = null;
    this.closed.emit();
  }

  formatTime(time: string | undefined): string {
    return time || '--:--';
  }

  statusLabel(status: ReceptionCalendarReservation['visualStatus']): string {
    switch (status) {
      case 'active': return 'Vigente';
      case 'upcoming': return 'Próxima';
      case 'past': return 'Finalizada';
      case 'cancelled': return 'Cancelada';
    }
  }

  reload(): void {
    this.detailResource.reload();
  }
}
