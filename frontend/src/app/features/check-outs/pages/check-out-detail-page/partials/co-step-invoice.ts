import { CurrencyPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChangeDetectionStrategy, Component, effect, inject, input, output, signal } from '@angular/core';

import { CheckOutsApiService, type CheckOutInvoiceDto } from '../../../services/check-outs-api.service';
import { ConfirmDialogService } from '../../../../../shared/ui/confirm-dialog/confirm-dialog.service';

@Component({
  selector: 'app-co-step-invoice',
  standalone: true,
  imports: [CurrencyPipe, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="co-card co-step-card co-invoice-card">
      <div class="co-step-badge">Paso 4</div>
      <h2 class="co-step-title">Emitir factura</h2>

      @if (invoiceGenerated()) {
        <div class="co-invoice-success">
          <span class="material-symbols-outlined">check_circle</span>
          <span>Factura {{ invoiceNumber() }} disponible</span>
          @if (existingInvoice()?.status) {
            <span class="co-invoice-status">{{ existingInvoice()!.status }}</span>
          }
        </div>

        <div class="co-invoice-summary">
          <div class="co-invoice-summary-head">
            <div>
              <span class="co-invoice-summary-kicker">Comprobante fiscal</span>
              <strong>{{ invoiceNumber() }}</strong>
            </div>
            <span class="material-symbols-outlined">receipt_long</span>
          </div>
          <div class="co-invoice-summary-rows">
            <div><span>Subtotal</span><strong>{{ (existingInvoice()?.subtotal ?? subtotal()) | currency:currency() }}</strong></div>
            <div><span>Impuestos</span><strong>{{ (existingInvoice()?.taxes ?? taxes()) | currency:currency() }}</strong></div>
            <div class="co-invoice-summary-total"><span>Total</span><strong>{{ (existingInvoice()?.total ?? (subtotal() + taxes())) | currency:currency() }}</strong></div>
          </div>
        </div>
      }

      <div class="co-invoice-actions">
        <button class="co-inv-btn co-inv-primary"
                [disabled]="generating() || invoiceGenerated()"
                (click)="emitInvoice()">
          <span class="material-symbols-outlined">receipt</span>
          <span class="co-inv-btn-label">
            @if (generating()) {
              <span class="material-symbols-outlined rc-spin" style="font-size:16px;vertical-align:middle">progress_activity</span>
              Generando...
            } @else if (invoiceGenerated()) {
              Factura Emitida
            } @else {
              Emitir Factura
            }
          </span>
          <span class="co-inv-btn-sub">Generar CFDI / factura fiscal</span>
        </button>

        @if (reconcileGap() > 0 && invoiceGenerated()) {
          <button class="co-inv-btn co-inv-complement"
                  [disabled]="complementing() || generating()"
                  (click)="emitComplementInvoice()">
            <span class="material-symbols-outlined">receipt_long</span>
            <span class="co-inv-btn-label">
              @if (complementing()) {
                <span class="material-symbols-outlined rc-spin" style="font-size:16px;vertical-align:middle">progress_activity</span>
                Emitiendo...
              } @else {
                Re-facturar gap
              }
            </span>
            <span class="co-inv-btn-sub">Complementaria por {{ reconcileGap() | currency:currency() }}</span>
          </button>
        }

        <button class="co-inv-btn"
                [disabled]="emailing() || !invoiceGenerated()"
                (click)="sendByEmail()">
          <span class="material-symbols-outlined">mail</span>
          <span class="co-inv-btn-label">
            @if (emailing()) {
              Enviando...
            } @else if (emailSent()) {
              Enviado ✓
            } @else {
              Enviar por Correo
            }
          </span>
          <span class="co-inv-btn-sub">Al hu&eacute;sped: {{ guestEmail() }}</span>
        </button>

        <button class="co-inv-btn"
                [disabled]="!invoiceGenerated()"
                (click)="printInvoice()">
          <span class="material-symbols-outlined">print</span>
          <span class="co-inv-btn-label">Imprimir</span>
          <span class="co-inv-btn-sub">Recibo / comprobante</span>
        </button>
      </div>

      @if (complementMsg()) {
        <div class="co-invoice-success">{{ complementMsg() }}</div>
      }

      @if (errorMsg()) {
        <div class="co-invoice-error">{{ errorMsg() }}</div>
      }

      <label class="co-check co-split-check" [class.co-checked]="splitInvoice()">
        <input type="checkbox" [ngModel]="splitInvoice()" (ngModelChange)="splitInvoiceChange.emit($event)" />
        <span>Factura separada para consumos</span>
        @if (splitInvoice()) { <span class="co-check-icon material-symbols-outlined">check_circle</span> }
      </label>

      @if (showNavigation()) {
        <div class="co-step-actions">
          <button class="co-btn-outline" (click)="prev.emit()">&larr; Atr&aacute;s</button>
          <button class="co-btn-primary" (click)="next.emit()">Continuar &rarr;</button>
        </div>
      }
    </section>
  `
})
export class CoStepInvoiceComponent {
  private readonly api = inject(CheckOutsApiService);
  private readonly confirmDialog = inject(ConfirmDialogService);

  readonly guestEmail = input('');
  readonly existingInvoice = input<CheckOutInvoiceDto | null>(null);
  readonly showNavigation = input(true);
  readonly splitInvoice = input(false);
  readonly bookingId = input('');
  readonly propId = input(0);
  readonly subtotal = input(0);
  readonly taxes = input(0);
  readonly currency = input('USD');
  /** Gap de la factura corta (subtotal vivo − covered_subtotal). > 0 muestra
   *  la acción de re-facturación; 0 la oculta. */
  readonly reconcileGap = input(0);

  readonly prev = output<void>();
  readonly next = output<void>();
  readonly splitInvoiceChange = output<boolean>();
  readonly invoiceEmitted = output<string>();
  readonly complementEmitted = output<string>();

  readonly generating = signal(false);
  readonly emailing = signal(false);
  readonly emailSent = signal(false);
  readonly invoiceGenerated = signal(false);
  readonly invoiceId = signal('');
  readonly invoiceNumber = signal('');
  readonly errorMsg = signal('');
  readonly complementing = signal(false);
  readonly complementMsg = signal('');

  constructor() {
    // Keep the action buttons usable after the detail resource reloads. The
    // invoice may have been issued before this page was opened, so local state
    // cannot be the only source of truth.
    effect(() => {
      const invoice = this.existingInvoice();
      if (!invoice) return;
      this.invoiceGenerated.set(invoice.status !== 'cancelled');
      this.invoiceId.set(invoice.id);
      this.invoiceNumber.set(invoice.invoice_number);
    }, { allowSignalWrites: true });
  }

  emitInvoice(): void {
    const bookingId = this.bookingId();
    const propId = this.propId();
    if (!bookingId || !propId) return;

    this.generating.set(true);
    this.errorMsg.set('');

    this.api.emitInvoice(bookingId, propId, this.subtotal(), this.taxes()).subscribe({
      next: (result) => {
        this.generating.set(false);
        this.invoiceGenerated.set(true);
        this.invoiceId.set(result.id);
        this.invoiceNumber.set(result.invoice_number);
        this.invoiceEmitted.emit(result.id);
      },
      error: (err) => {
        this.generating.set(false);
        this.errorMsg.set(
          err?.error?.detail ||
          'No se pudo emitir la factura. Revisá el subtotal y los impuestos de la liquidación e intentá de nuevo.',
        );
        setTimeout(() => this.errorMsg.set(''), 6000);
      },
    });
  }

  /** Emite la factura complementaria por el gap (cargos nuevos no cubiertos
   *  por la factura principal). Idempotente en backend: tras el reload del
   *  detalle, covered_subtotal cubre el subtotal vivo y la nota/acción
   *  desaparecen. */
  emitComplementInvoice(): void {
    const bookingId = this.bookingId();
    const propId = this.propId();
    if (!bookingId || !propId || this.reconcileGap() <= 0) return;

    this.complementing.set(true);
    this.errorMsg.set('');
    this.complementMsg.set('');

    this.api.emitComplementInvoice(bookingId, propId).subscribe({
      next: (result) => {
        this.complementing.set(false);
        this.complementMsg.set(`Factura complementaria ${result.invoice_number} emitida por el gap.`);
        this.complementEmitted.emit(result.id);
        setTimeout(() => this.complementMsg.set(''), 8000);
      },
      error: (err) => {
        this.complementing.set(false);
        this.errorMsg.set(
          err?.error?.detail ||
          'No se pudo emitir la factura complementaria. Verificá que el folio esté abierto y que haya cargos nuevos sin facturar, e intentá de nuevo.',
        );
        setTimeout(() => this.errorMsg.set(''), 6000);
      },
    });
  }

  async sendByEmail(): Promise<void> {
    const invoiceId = this.invoiceId();
    if (!invoiceId) return;

    const ok = await this.confirmDialog.open({
      title: 'Enviar factura por correo',
      message: `¿Deseas enviar la factura ${this.invoiceNumber() || invoiceId} al huésped?`,
      confirmLabel: 'Enviar',
      variant: 'default',
    });
    if (!ok) return;

    this.emailing.set(true);
    this.errorMsg.set('');

    this.api.sendInvoiceEmail(invoiceId, this.propId()).subscribe({
      next: () => {
        this.emailing.set(false);
        this.emailSent.set(true);
      },
      error: (err) => {
        this.emailing.set(false);
        this.errorMsg.set(
          err?.error?.detail ||
          'No se pudo enviar el correo. Verificá que el huésped tenga un email válido e intentá de nuevo.',
        );
        setTimeout(() => this.errorMsg.set(''), 6000);
      },
    });
  }

  async printInvoice(): Promise<void> {
    const ok = await this.confirmDialog.open({
      title: 'Imprimir comprobante',
      message: '¿Deseas imprimir el recibo / comprobante de esta factura?',
      confirmLabel: 'Imprimir',
      variant: 'default',
    });
    if (!ok) return;
    window.print();
  }
}
