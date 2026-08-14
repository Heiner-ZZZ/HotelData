import { Component, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { OnInit } from '@angular/core';

import { BillingApiService } from '../../services/billing-api.service';
import type { ShiftCandidate } from '../../models/billing.model';

/**
 * Modal para vincular un pago legacy (sin atribución de turno) al turno
 * responsable. Carga los turnos candidatos del hotel del pago y permite
 * elegir uno; al confirmar llama al API de vínculo que estampa `shift_id`
 * + empleado/opener en el pago y su espejo de hechos.
 */
@Component({
  selector: 'app-link-shift-modal',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './link-shift-modal.html',
  styleUrl: './link-shift-modal.scss',
})
export class LinkShiftModalComponent implements OnInit {
  private readonly billingApi = inject(BillingApiService);

  readonly paymentId = input.required<string>();
  readonly propId = input.required<number>();
  readonly paymentReference = input<string | null>(null);

  readonly close = output<void>();
  /** Emits when the payment was successfully linked (parent reloads + toasts). */
  readonly linked = output<void>();

  readonly candidates = signal<ShiftCandidate[]>([]);
  readonly loading = signal(true);
  readonly loadError = signal<string | null>(null);
  readonly selectedShiftId = signal<string>('');
  readonly submitting = signal(false);
  readonly submitError = signal<string | null>(null);

  ngOnInit(): void {
    this.loadCandidates();
  }

  private loadCandidates(): void {
    this.loading.set(true);
    this.loadError.set(null);
    this.billingApi.getPaymentLinkCandidates(this.paymentId(), this.propId()).subscribe({
      next: (result) => {
        this.candidates.set(result.shifts);
        const open = result.shifts.find((s) => s.status === 'open');
        this.selectedShiftId.set(open?.id ?? result.shifts[0]?.id ?? '');
        this.loading.set(false);
      },
      error: () => {
        this.loadError.set('No se pudieron cargar los turnos del hotel.');
        this.loading.set(false);
      },
    });
  }

  selectShift(id: string): void {
    this.selectedShiftId.set(id);
    this.submitError.set(null);
  }

  shiftLabel(shift: ShiftCandidate): string {
    const type = shift.shiftType ?? 'turno';
    const when = shift.startTime
      ? ` · ${new Date(shift.startTime).toLocaleString('es-PE', { dateStyle: 'short', timeStyle: 'short' })}`
      : '';
    const who = shift.employee || shift.openedBy || 'sin responsable';
    const state = shift.status === 'open' ? 'Abierto' : 'Cerrado';
    return `${type}${when} · ${who} · ${state}`;
  }

  confirm(): void {
    const shiftId = this.selectedShiftId();
    if (!shiftId) {
      this.submitError.set('Selecciona un turno para vincular el pago.');
      return;
    }
    this.submitting.set(true);
    this.submitError.set(null);
    this.billingApi.linkPaymentToShift(this.paymentId(), shiftId, this.propId()).subscribe({
      next: () => {
        this.submitting.set(false);
        this.linked.emit();
      },
      error: (err) => {
        this.submitting.set(false);
        this.submitError.set(
          err?.error?.detail || err?.message || 'No se pudo vincular el pago al turno.',
        );
      },
    });
  }
}
