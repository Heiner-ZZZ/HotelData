import { FormsModule } from '@angular/forms';
import { ChangeDetectionStrategy, Component, inject, input, output, signal } from '@angular/core';

import { CheckOutsApiService } from '../../../services/check-outs-api.service';
import { ConfirmDialogService } from '../../../../../shared/ui/confirm-dialog/confirm-dialog.service';

@Component({
  selector: 'app-co-step-invoice',
  standalone: true,
  imports: [FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="co-card co-step-card">
      <div class="co-step-badge">Paso 4</div>
      <h2 class="co-step-title">Emitir factura</h2>

      @if (invoiceGenerated()) {
        <div class="co-invoice-success">
          <span class="material-symbols-outlined">check_circle</span>
          Factura {{ invoiceNumber() }} generada
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

      @if (errorMsg()) {
        <div class="co-invoice-error">{{ errorMsg() }}</div>
      }

      <label class="co-check co-split-check" [class.co-checked]="splitInvoice()">
        <input type="checkbox" [ngModel]="splitInvoice()" (ngModelChange)="splitInvoiceChange.emit($event)" />
        <span>Factura separada para consumos</span>
        @if (splitInvoice()) { <span class="co-check-icon material-symbols-outlined">check_circle</span> }
      </label>

      <div class="co-step-actions">
        <button class="co-btn-outline" (click)="prev.emit()">&larr; Atr&aacute;s</button>
        <button class="co-btn-primary" (click)="next.emit()">Continuar &rarr;</button>
      </div>
    </section>
  `
})
export class CoStepInvoiceComponent {
  private readonly api = inject(CheckOutsApiService);
  private readonly confirmDialog = inject(ConfirmDialogService);

  readonly guestEmail = input('');
  readonly splitInvoice = input(false);
  readonly bookingId = input('');
  readonly propId = input(0);
  readonly subtotal = input(0);
  readonly taxes = input(0);

  readonly prev = output<void>();
  readonly next = output<void>();
  readonly splitInvoiceChange = output<boolean>();
  readonly invoiceEmitted = output<string>();

  readonly generating = signal(false);
  readonly emailing = signal(false);
  readonly emailSent = signal(false);
  readonly invoiceGenerated = signal(false);
  readonly invoiceId = signal('');
  readonly invoiceNumber = signal('');
  readonly errorMsg = signal('');

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
        this.errorMsg.set(err?.error?.detail || 'Error al emitir la factura');
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

    this.api.sendInvoiceEmail(invoiceId).subscribe({
      next: () => {
        this.emailing.set(false);
        this.emailSent.set(true);
      },
      error: (err) => {
        this.emailing.set(false);
        this.errorMsg.set(err?.error?.detail || 'Error al enviar el correo');
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
