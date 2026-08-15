import { ChangeDetectionStrategy, Component, computed, DestroyRef, effect, ElementRef, HostListener, inject, input, output, signal, ViewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DecimalPipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { Router, RouterLink } from '@angular/router';
import { CdkTrapFocus } from '@angular/cdk/a11y';
import type { ReceptionCalendarReservation } from '../../models/reception-calendar.model';
import type { ReservationDetailDto } from '../../models/reservations.dto';
import type { ReservationDetailViewModel } from '../../models/reservations.model';
import { mapReservationDetail } from '../../mappers/reservations.mapper';
import { InStayApiService } from '../../../in-stay/services/in-stay-api.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { AuthService } from '../../../../core/auth/auth.service';
import { CHECK_INS_NO_SHOW_REOPEN } from '../../../../core/auth/permission.constants';
import { CheckInsApiService } from '../../../check-ins/services/check-ins-api.service';

@Component({
  selector: 'app-reservation-detail-modal',
  imports: [CdkTrapFocus, DecimalPipe, RouterLink],
  templateUrl: './reservation-detail-modal.html',
  styleUrl: './reservation-detail-modal.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReservationDetailModalComponent {
  private readonly router = inject(Router);
  private readonly instayApi = inject(InStayApiService);
  private readonly toast = inject(ToastService);
  private readonly auth = inject(AuthService);
  private readonly checkInsApi = inject(CheckInsApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly reservation = input.required<ReceptionCalendarReservation>();
  readonly presentation = input<'modal' | 'side-panel'>('modal');
  readonly closed = output<void>();
  /** Emitido tras reabrir un no-show: el calendario recarga sus barras. */
  readonly reopened = output<void>();

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

  /**
   * Estado operativo de la estancia para el aviso inline del modal, sin
   * necesidad de navegar a otra página: verde si el check-in está hecho,
   * ámbar (warning) si falta el check-in o hubo no-show.
   *
   * Para el caso pending se informa además la fecha límite de check-in y
   * cuánto falta para que la reserva sea candidata a no-show (cuando la
   * fecha ya pasó, el scheduler diario o el staff pueden marcarla en
   * cualquier momento).
   */
  readonly stayAlert = computed(() => {
    const detail = this.detailResource.value();
    const stay = detail?.stayStatus ?? '';
    if (stay === 'checked_in') {
      return {
        kind: 'success' as const,
        icon: 'check_circle',
        message: 'Check-in realizado — estancia activa.',
      };
    }
    if (stay === 'checked_out') {
      return {
        kind: 'info' as const,
        icon: 'logout',
        message: 'Check-out realizado — estancia finalizada.',
      };
    }
    if (stay === 'no_show') {
      // Ventana de reapertura (hoy/ayer + estadía vigente) reflejada en el
      // calendario: la acción se ofrece solo dentro de la ventana y el copy
      // orienta a ajustar fechas / crear reserva cuando cerró.
      const window = this.reservation().reopenWindow;
      if (window === 'open') {
        return {
          kind: 'warning' as const,
          icon: 'replay',
          message: 'No show — el huésped no llegó. Ventana de reapertura abierta (hoy o ayer con estadía vigente): podés reabrir la reserva.',
        };
      }
      if (window === 'too_late') {
        return {
          kind: 'danger' as const,
          icon: 'event_busy',
          message: 'No show — ventana de reapertura cerrada (check-in con más de un día de retraso). Ajustá las fechas o creá una reserva nueva.',
        };
      }
      if (window === 'stay_ended') {
        return {
          kind: 'danger' as const,
          icon: 'event_busy',
          message: 'No show — la estadía ya terminó y la ventana de reapertura cerró. Ajustá las fechas o creá una reserva nueva.',
        };
      }
      return {
        kind: 'warning' as const,
        icon: 'warning',
        message: 'No show — el huésped no llegó.',
      };
    }
    return this.pendingStayAlert(detail?.checkInDate ?? this.reservation().checkInDate);
  });

  /**
   * Aviso cuando el check-in sigue pendiente: muestra la fecha límite y los
   * días restantes antes de que la reserva sea candidata a no-show.
   */
  private pendingStayAlert(checkInDate: string | undefined): {
    kind: 'warning';
    icon: string;
    message: string;
  } {
    const iso = checkInDate?.slice(0, 10) ?? '';
    if (!iso || Number.isNaN(new Date(`${iso}T12:00:00`).getTime())) {
      return {
        kind: 'warning',
        icon: 'warning',
        message: 'No se ha realizado el check-in. La estadía aún no está activa.',
      };
    }
    const limit = new Date(`${iso}T12:00:00`);
    const today = new Date();
    today.setHours(12, 0, 0, 0);
    const daysLeft = Math.round((limit.getTime() - today.getTime()) / 86_400_000);
    const limitLabel = new Intl.DateTimeFormat('es-MX', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    }).format(limit);

    if (daysLeft > 0) {
      const plural = daysLeft === 1 ? 'día' : 'días';
      return {
        kind: 'warning',
        icon: 'warning',
        message: `Check-in pendiente — el ${limitLabel} (en ${daysLeft} ${plural}) se marcará como no-show si nadie llega.`,
      };
    }
    if (daysLeft === 0) {
      return {
        kind: 'warning',
        icon: 'warning',
        message: `Check-in pendiente — la fecha límite es hoy (${limitLabel}). Si nadie llega hoy, la reserva es candidata a no-show.`,
      };
    }
    return {
      kind: 'warning',
      icon: 'warning',
      message: `Check-in pendiente — la fecha límite (${limitLabel}) ya pasó. La reserva puede marcarse como no-show en cualquier momento.`,
    };
  }

  /** Mi Estancia solo es accesible cuando la reserva ya pasó por check-in. */
  readonly canGoToStay = computed(() =>
    this.detailResource.value()?.stayStatus === 'checked_in',
  );

  // ── Reapertura de no-show (autorización de gerente) ──
  // La acción aparece SOLO dentro de la ventana (hoy/ayer + estadía vigente)
  // y con el permiso gerencial; en los no-shows antiguos se oculta.
  readonly canReopenNoShow = computed(() =>
    this.reservation().stayStatus === 'no_show' &&
    this.reservation().reopenWindow === 'open' &&
    this.auth.hasPermission(CHECK_INS_NO_SHOW_REOPEN),
  );

  readonly reopenDialogOpen = signal(false);
  readonly reopenReason = signal('');
  readonly reopenPending = signal(false);
  readonly reopenError = signal('');

  openReopenDialog(): void {
    if (!this.canReopenNoShow()) return;
    this.reopenReason.set('');
    this.reopenError.set('');
    this.reopenDialogOpen.set(true);
    queueMicrotask(() => document.getElementById('rd-reopen-reason')?.focus());
  }

  cancelReopenDialog(): void {
    this.reopenDialogOpen.set(false);
    this.reopenError.set('');
  }

  confirmReopenNoShow(): void {
    const reason = this.reopenReason().trim();
    if (!reason) {
      this.reopenError.set('Escribe el motivo de la reapertura antes de continuar.');
      return;
    }
    this.reopenPending.set(true);
    this.reopenError.set('');
    this.checkInsApi.reopenNoShow(this.reservation().bookingId, reason)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.reopenPending.set(false);
          this.reopenDialogOpen.set(false);
          this.toast.success('Reserva reabierta — el huésped puede hacer check-in.');
          this.detailResource.reload();
          this.reopened.emit();
        },
        error: (err: { message?: string }) => {
          this.reopenPending.set(false);
          this.reopenError.set(err.message || 'No fue posible reabrir la reserva.');
        },
      });
  }

  reload(): void {
    this.detailResource.reload();
  }

  /**
   * Abre la estadía (portal de Mi Estancia) de la reserva vigente. El token de
   * sesión se resuelve en el backend (``/api/stay/my-session``) y la ruta
   * ``/stay/{token}`` es la que monta el GuestPortal. Mismo patrón que
   * ``goToInStay`` en reservation-detail-page.
   */
  goToStay(): void {
    const bookingId = this.reservation().bookingId;
    if (!bookingId) return;
    this.instayApi.getMyStaySession(bookingId).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (session) => {
        if (session.token) {
          void this.router.navigate(['/stay', session.token]);
        }
      },
      error: () => {
        this.toast.error('No se pudo acceder a Mi Estancia. ¿Ya hiciste check-in?');
      },
    });
  }
}
