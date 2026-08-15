import { DatePipe } from '@angular/common';
import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { forkJoin, map } from 'rxjs';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ApiError } from '../../../../core/api/api-error.model';
import type { BillableServices, InvoiceDetailViewModel, LineItem, PaymentItem } from '../../models/billing.model';
import type { BillableServicesDto, InvoiceDetailDto } from '../../models/billing.dto';
import { mapBillableServices, mapInvoiceDetail } from '../../mappers/billing.mapper';
import { BillingApiService } from '../../services/billing-api.service';
import { FolioApiService } from '../../services/folio-api.service';
// Import amenityIcon from the amenities feature — resolves Material Symbols icons from amenity labels
import { amenityIcon } from '../../../amenities/utils/amenity-icons';
import { AuthService } from '../../../../core/auth/auth.service';
import { REPORTS_DOWNLOAD } from '../../../../core/auth/permission.constants';

@Component({
  selector: 'app-invoice-detail-page',
  imports: [DatePipe, RouterLink, FormsModule, ErrorStateComponent, LoadingStateComponent],
  templateUrl: './invoice-detail-page.html',
  styleUrl: './invoice-detail-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class InvoiceDetailPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly billingApi = inject(BillingApiService);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly folioApi = inject(FolioApiService);
  private readonly router = inject(Router);
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly auth = inject(AuthService);

  /** Descarga del PDF de la factura gateada por ``reports.download``. */
  readonly canExport = computed(() => this.auth.hasPermission(REPORTS_DOWNLOAD));

  private readonly routePropId = toSignal(
    this.activatedRoute.queryParamMap.pipe(map(params => Number(params.get('prop_id') ?? '0'))),
    { initialValue: 0 },
  );

  private readonly invoiceId = toSignal(
    this.activatedRoute.paramMap.pipe(map(params => params.get('invoiceId') ?? '')),
    { initialValue: '' }
  );

  readonly invoiceResource = httpResource<InvoiceDetailViewModel>(() => {
    const id = this.invoiceId();
    const propId = this.propertyCtx.currentPropId() || this.routePropId();
    return id && propId > 0 ? `/api/billing/invoices/${id}?prop_id=${propId}` : undefined;
  }, {
    parse: (res) => mapInvoiceDetail(res as InvoiceDetailDto),
  });

  readonly servicesResource = httpResource<BillableServices>(() => {
    const inv = this.invoiceResource.value();
    if (!inv?.propId) return undefined;
    const bookingParam = inv.bookingId ? `&booking_id=${inv.bookingId}` : '';
    return `/api/billing/services?prop_id=${inv.propId}${bookingParam}`;
  }, {
    parse: (res) => mapBillableServices(res as BillableServicesDto),
  });

  readonly viewState = computed<ViewState>(() => {
    if (this.invoiceResource.isLoading()) return 'loading';
    if (this.invoiceResource.error()) return 'error';
    return this.invoiceResource.value() ? 'success' : 'loading';
  });

  readonly invoice = computed(() => this.invoiceResource.value() ?? null);
  readonly servicesLoading = computed(() => this.servicesResource.isLoading());
  readonly actionError = signal<string | null>(null);
  readonly actionMessage = signal<string | null>(null);
  readonly addMode = signal(false);
  readonly quickAddMode = signal(false);
  readonly addBusy = signal(false);
  readonly quickAddBusy = signal<string | null>(null);
  readonly removeBusy = signal<string | null>(null);

  // Services (amenities) fetched from the API — replaces hardcoded CHARGE_CATEGORIES / QUICK_CHARGES
  readonly services = computed(() => this.servicesResource.value()?.all_items ?? []);

  /** Flat list of all available service categories for the add-charge dropdown. */
  readonly categories = computed(() => {
    const items = this.services();
    // Build from API data: group name taken from parent category, label as display
    return [
      ...items.map(item => ({
        id: item.label.toLowerCase().replace(/\s+/g, '_'),
        label: item.label,
        icon: amenityIcon(item.label),
      })),
      // Always include a generic "Otros" fallback
      { id: 'otros', label: 'Otros', icon: 'more_horiz' },
    ];
  });

  /** Quick-charge buttons: chargeable services (unit_price > 0) with a default quantity of 1. */
  readonly quickCharges = computed(() => {
    return this.services()
      .filter(item => item.unitPrice > 0)
      .map(item => ({
        name: item.label,
        category: item.label.toLowerCase().replace(/\s+/g, '_'),
        icon: amenityIcon(item.label),
        amount: item.unitPrice,
        quantity: 1,
      }));
  });

  // Add charge form
  readonly addForm = signal({
    name: '',
    category: 'otros',
    quantity: 1,
    unit_price: 0,
  });

  readonly isPaid = computed(() => this.invoice()?.status === 'paid');
  readonly isCancelled = computed(() => this.invoice()?.status === 'cancelled');
  readonly isVoided = computed(() => this.invoice()?.status === 'cancelled' || this.invoice()?.status === 'refunded');
  readonly isIssued = computed(() => this.invoice()?.status === 'issued');
  readonly accountingRepairPending = computed(() => this.isVoided() && this.invoice()?.accountingStatus !== 'reversed');
  readonly accountingRepairBusy = signal(false);
  readonly creditNoteBusy = signal(false);
  readonly creditNotePending = computed(() => this.isVoided() && !this.invoice()?.creditNoteNumber);

  readonly subtotal = computed(() => this.invoice()?.subtotal ?? 0);
  readonly taxes = computed(() => this.invoice()?.taxes ?? 0);
  readonly total = computed(() => this.invoice()?.total ?? 0);
  readonly totalPaidAmount = computed(() => this.invoice()?.totalPaidAmount ?? 0);
  readonly totalPendingAmount = computed(() => this.invoice()?.totalPendingAmount ?? 0);
  readonly lineItems = computed(() => this.invoice()?.lineItems ?? []);
  readonly payments = computed(() => this.invoice()?.payments ?? []);

  readonly totalLiteral = computed(() => {
    const t = this.total();
    if (t === 0) return 'Cero pesos 00/100 M.N.';
    const intPart = Math.floor(t);
    const decPart = Math.round((t - intPart) * 100);
    return `${_numToWords(intPart)} pesos ${String(decPart).padStart(2, '0')}/100 M.N.`;
  });

  readonly statusLabel = computed(() => {
    const s = this.invoice()?.status;
    if (s === 'paid') return 'Pagada';
    if (s === 'cancelled') return 'Anulada';
    if (s === 'refunded') return 'Reembolsada';
    return 'Emitida';
  });

  readonly statusTone = computed(() => {
    const s = this.invoice()?.status;
    if (s === 'paid') return 'success';
    if (s === 'cancelled' || s === 'refunded') return 'danger';
    return 'warning';
  });

  readonly taxRate = computed(() => {
    const s = this.subtotal();
    const t = this.taxes();
    return s > 0 ? (t / s) * 100 : 0;
  });

  readonly canModify = computed(() => this.isIssued());

  constructor() {}

  /** Starts the add-charge flow. */
  openAddForm(): void {
    this.addMode.set(true);
    this.actionError.set(null);
    this.addForm.set({ name: '', category: 'otros', quantity: 1, unit_price: 0 });
  }

  closeAddForm(): void {
    this.addMode.set(false);
    this.actionError.set(null);
  }

  /** Submit a new line item to the invoice. */
  submitAddItem(): void {
    const form = this.addForm();
    if (!form.name || form.unit_price <= 0) {
      this.actionError.set('El concepto y el precio unitario son obligatorios. Completá ambos campos para agregar el cargo.');
      return;
    }
    this.addBusy.set(true);
    this.actionError.set(null);
    this.actionMessage.set(null);

    this.billingApi.addLineItem(this.invoice()!.id, {
      name: form.name,
      quantity: form.quantity,
      unit_price: form.unit_price,
      category: form.category,
    }, this.invoice()!.propId as number).subscribe({
      next: () => {
        this.invoiceResource.reload();
        this.actionMessage.set(`Cargo "${form.name}" agregado a la factura.`);
        this.addMode.set(false);
        this.addBusy.set(false);
      },
      error: () => {
        this.actionError.set('No se pudo agregar el cargo. Verificá que la factura esté emitida y sin pagos confirmados, e intentá de nuevo.');
        this.addBusy.set(false);
      },
    });
  }

  /** Remove a line item from the invoice. */
  async removeItem(item: LineItem): Promise<void> {
    if (item.itemId.startsWith('room_')) {
      this.actionError.set('El cargo de habitación no se puede eliminar. Anulá la factura si necesitás corregirlo.');
      return;
    }
    const ok = await this.confirmDialog.open({
      title: 'Eliminar concepto',
      message: `¿Eliminar "${item.name}" de la factura?`,
      confirmLabel: 'Eliminar',
      variant: 'danger',
      mode: 'delete',
      modeDetail: item.name,
    });
    if (!ok) return;
    this.removeBusy.set(item.itemId);
    this.actionError.set(null);
    this.actionMessage.set(null);

    this.billingApi.removeLineItem(this.invoice()!.id, item.itemId, this.invoice()!.propId as number).subscribe({
      next: () => {
        this.invoiceResource.reload();
        this.actionMessage.set(`Concepto "${item.name}" eliminado de la factura.`);
        this.removeBusy.set(null);
      },
      error: () => {
        this.actionError.set('No se pudo eliminar el concepto. Verificá que la factura esté emitida y elegí un concepto que no sea el cargo de habitación, e intentá de nuevo.');
        this.removeBusy.set(null);
      },
    });
  }

  /** Quick-add: post to folio AND add to invoice simultaneously. */
  quickAddCharge(qc: { name: string; category: string; icon: string; amount: number; quantity: number }): void {
    const inv = this.invoice();
    if (!inv || !inv.folioId) {
      this.actionError.set('No hay folio asociado para registrar el cargo. Verificá que la reserva tenga un folio abierto antes de agregar el concepto.');
      return;
    }
    this.quickAddBusy.set(qc.name);
    this.actionError.set(null);
    this.actionMessage.set(null);

    // Post to folio + add to invoice in parallel
    forkJoin({
      folio: this.folioApi.postToFolio(inv.bookingId, {
        posting_type: 'charge',
        category: qc.category,
        concept: qc.name,
        amount: qc.amount * qc.quantity,
        quantity: qc.quantity,
        reference_type: 'quick_charge',
      }),
      invoice: this.billingApi.addLineItem(inv.id, {
        name: qc.name,
        quantity: qc.quantity,
        unit_price: qc.amount,
        category: qc.category,
      }, inv.propId as number),
    }).subscribe({
      next: () => {
        this.invoiceResource.reload();
        this.actionMessage.set(`Cargo "${qc.name}" ($ ${(qc.amount * qc.quantity).toFixed(2)}) agregado al folio y la factura.`);
        this.quickAddBusy.set(null);
      },
      error: () => {
        this.actionError.set(`No se pudo agregar "${qc.name}" al folio/factura. Verificá que haya un turno de caja activo y que la factura esté emitida, e intentá de nuevo.`);
        this.quickAddBusy.set(null);
      },
    });
  }

  issueCreditNote(): void {
    const invoice = this.invoice();
    if (!invoice || !this.creditNotePending()) return;
    this.creditNoteBusy.set(true);
    this.actionError.set(null);
    this.actionMessage.set(null);
    this.billingApi.createCreditNote(invoice.id, invoice.propId as number).subscribe({
      next: () => {
        this.actionMessage.set('Documento compensatorio emitido y enlazado al libro mayor.');
        this.creditNoteBusy.set(false);
        this.invoiceResource.reload();
      },
      error: () => {
        this.actionError.set('No se pudo emitir el documento compensatorio. Verificá que la factura esté anulada o reembolsada y que haya un turno de caja activo, e intentá de nuevo.');
        this.creditNoteBusy.set(false);
      },
    });
  }

  repairSettlement(): void {
    const invoice = this.invoice();
    if (!invoice || !this.accountingRepairPending()) return;
    this.accountingRepairBusy.set(true);
    this.actionError.set(null);
    this.actionMessage.set(null);
    this.billingApi.repairInvoiceSettlement(invoice.id, invoice.propId as number).subscribe({
      next: () => {
        this.actionMessage.set('Valor neto y reversión contable corregidos; el importe original se conserva.');
        this.accountingRepairBusy.set(false);
        this.invoiceResource.reload();
      },
      error: () => {
        this.actionError.set('No se pudo corregir la reversión contable de la factura. Verificá que la factura esté anulada o reembolsada y que tenga importe positivo, e intentá de nuevo.');
        this.accountingRepairBusy.set(false);
      },
    });
  }

  async payInvoice(): Promise<void> {
    const ok = await this.confirmDialog.open({
      title: 'Registrar pago',
      message: `¿Registrar el pago de esta factura? Se procesará un cobro de $${this.total().toFixed(2)}.`,
      confirmLabel: 'Registrar pago',
      variant: 'warning',
    });
    if (!ok) return;
    this.actionError.set(null);
    this.actionMessage.set(null);
    this.billingApi.payInvoice(this.invoice()!.id, this.invoice()!.propId as number).subscribe({
      next: () => {
        this.actionMessage.set('Pago procesado exitosamente.');
        this.invoiceResource.reload();
      },
      error: () => this.actionError.set('No se pudo procesar el pago. Verificá que la factura esté emitida y que haya un turno de caja activo, e intentá de nuevo.'),
    });
  }

  async cancelInvoice(): Promise<void> {
    const reason = await this.confirmDialog.openPrompt({
      title: 'Anular factura',
      message: '¿Anular esta factura? Esta acción no se puede deshacer.',
      confirmLabel: 'Anular factura',
      variant: 'danger',
      // Anulación = estado permanente → mostrar modo delete mientras se confirma.
      mode: 'delete',
      modeDetail: `Factura ${this.invoice()?.id ?? ''}`,
      input: {
        label: 'Motivo de la anulación (opcional)',
        placeholder: 'Ej. Factura duplicada, error en el cobro…',
        maxLength: 500,
      },
    });
    if (reason === null) return;
    this.actionError.set(null);
    this.actionMessage.set(null);
    this.billingApi.cancelInvoice(this.invoice()!.id, this.invoice()!.propId as number, reason).subscribe({
      next: () => {
        this.actionMessage.set('Factura anulada correctamente.');
        this.invoiceResource.reload();
      },
      error: (err: ApiError) => this.actionError.set(err.message || 'No se pudo anular la factura. Verificá que esté pendiente de pago y sin pagos confirmados, e intentá de nuevo.'),
    });
  }

  goBack(): void {
    void this.router.navigate(['/management/billing/invoices']);
  }

  printPage(): void {
    window.print();
  }

  categoryIcon(cat: string): string {
    // Resolve icon from amenity label using the central amenityIcon() function
    const label = cat.replace(/_/g, ' ');
    return amenityIcon(label) || 'receipt_long';
  }

  /** Whether a line item can be removed (not a room charge). */
  canRemove(item: LineItem): boolean {
    return !!item?.itemId && !item.itemId.startsWith('room_') && this.canModify();
  }

  paymentMethodLabel(method: string): string {
    const map: Record<string, string> = {
      simulated: 'Simulación',
      bank_transfer: 'Transferencia',
      credit_card: 'Tarjeta Crédito',
      cash: 'Efectivo',
      mix: 'Mixto',
    };
    return map[method] ?? method;
  }

  paymentMethodIcon(method: string): string {
    const map: Record<string, string> = {
      simulated: 'payments',
      bank_transfer: 'account_balance',
      credit_card: 'credit_card',
      cash: 'payments',
      mix: 'account_balance',
    };
    return map[method] ?? 'payments';
  }

  /** Responsible cashier label for a payment, or null when unattributed. */
  shiftLabel(p: PaymentItem): string | null {
    return p.shiftEmployee || p.shiftOpenedBy || null;
  }

  /** Human label of the shift type ("Matutino" / "Vespertino" / "Nocturno"). */
  shiftTypeLabel(type: string | null): string {
    const map: Record<string, string> = {
      morning: 'Matutino',
      afternoon: 'Vespertino',
      evening: 'Nocturno',
    };
    return (type && map[type]) || '';
  }

  /** Tooltip with the shift FK + type for full attribution. */
  shiftTitle(p: PaymentItem): string {
    const type = p.shiftType ? ` · ${p.shiftType}` : '';
    return p.shiftId ? `Turno ${p.shiftId}${type}` : 'Sin turno asociado';
  }

  readonly Math = Math;
}

/** Simple number to words converter for Spanish (supports 0-9999). */
function _numToWords(n: number): string {
  if (n === 0) return 'Cero';
  const units = ['', 'Un', 'Dos', 'Tres', 'Cuatro', 'Cinco', 'Seis', 'Siete', 'Ocho', 'Nueve'];
  const teens = ['Diez', 'Once', 'Doce', 'Trece', 'Catorce', 'Quince', 'Dieciséis', 'Diecisiete', 'Dieciocho', 'Diecinueve'];
  const tens = ['', '', 'Veinte', 'Treinta', 'Cuarenta', 'Cincuenta', 'Sesenta', 'Setenta', 'Ochenta', 'Noventa'];
  const hundreds = ['', 'Ciento', 'Doscientos', 'Trescientos', 'Cuatrocientos', 'Quinientos', 'Seiscientos', 'Setecientos', 'Ochocientos', 'Novecientos'];

  let words = '';
  if (n >= 1000) {
    const m = Math.floor(n / 1000);
    words += (m === 1 ? 'Mil' : _numToWords(m) + ' Mil') + ' ';
    n %= 1000;
  }
  if (n >= 100) {
    const c = Math.floor(n / 100);
    words += (c === 1 && n % 100 === 0 ? 'Cien' : hundreds[c]) + ' ';
    n %= 100;
  }
  if (n >= 20) {
    const t = Math.floor(n / 10);
    words += tens[t] + ' ';
    n %= 10;
    if (n > 0) words += 'y ';
  } else if (n >= 10) {
    words += teens[n - 10] + ' ';
    n = 0;
  }
  if (n > 0) {
    words += units[n] + ' ';
  }
  return words.trim();
}
