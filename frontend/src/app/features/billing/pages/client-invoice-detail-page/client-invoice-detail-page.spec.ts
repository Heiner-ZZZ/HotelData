import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';

import type { InvoiceDetailDto } from '../../models/billing.dto';
import { BillingApiService } from '../../services/billing-api.service';
import { ClientInvoiceDetailPageComponent } from './client-invoice-detail-page';

const DETAIL_DTO: InvoiceDetailDto = {
  _id: '6a763f7e34b2d2ce793f122d',
  booking_id: 'BK-20260807202628-71E570F9',
  invoice_number: 'INV-202608-0002',
  prop_id: 1,
  subtotal: 162.07,
  room_subtotal: 162.07,
  extras_total: 0,
  taxes: 25.93,
  total: 188.0,
  total_paid_amount: 0,
  total_pending_amount: 188.0,
  status: 'issued',
  issued_at: '2026-08-07T20:26:28Z',
  paid_at: null,
  notes: null,
  line_items: [],
  guest_name: 'Horuz',
  guest_email: 'horuz@hoteldata.local',
  guest_cedula: '',
  hotel_label: 'Hotel 1',
  check_in_date: '2026-08-20',
  check_out_date: '2026-08-22',
  total_nights: 2,
  rooms: 1,
  room_type_name: 'Deluxe',
  room_labels: [],
  payments: [],
  folio_id: null,
  folio_number: null,
} as InvoiceDetailDto;

describe('ClientInvoiceDetailPageComponent — copy de pago sin "simulado"', () => {
  async function render() {
    await TestBed.configureTestingModule({
      imports: [ClientInvoiceDetailPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { paramMap: of(new Map([['invoiceId', '6a763f7e34b2d2ce793f122d']])) } },
        { provide: Router, useValue: { navigate: jest.fn() } },
        { provide: BillingApiService, useValue: { payMyInvoice: jest.fn() } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ClientInvoiceDetailPageComponent);
    fixture.detectChanges();

    const httpTesting = TestBed.inject(HttpTestingController);
    const req = httpTesting.expectOne((r) => r.url.includes('/api/billing/my-invoices/6a763f7e34b2d2ce793f122d'));
    req.flush(DETAIL_DTO);

    await fixture.whenStable();
    await Promise.resolve();
    await Promise.resolve();
    fixture.detectChanges();
    return { fixture, httpTesting };
  }

  it('muestra la sección de pago con copy "Pago en línea" sin la palabra "simulado"', async () => {
    const { fixture } = await render();
    const rendered = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(rendered).toContain('Pago en línea');
    expect(rendered.toLowerCase()).not.toContain('simulado');
    expect(rendered).not.toContain('Transferencia bancaria simulada');
    expect(rendered).not.toContain('no hay movimiento de dinero real');
    fixture.destroy();
  });
});

describe('ClientInvoiceDetailPageComponent — formulario de tarjeta', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  async function render() {
    await TestBed.configureTestingModule({
      imports: [ClientInvoiceDetailPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ActivatedRoute, useValue: { paramMap: of(new Map([['invoiceId', '6a85ff8f5cf638c2b82e1daf']])) } },
        { provide: Router, useValue: { navigate: jest.fn() } },
        { provide: BillingApiService, useValue: { payMyInvoice: jest.fn(() => of({ ok: true, message: 'Pago procesado exitosamente', payment: { reference: 'HD-REF-1' } })) } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(ClientInvoiceDetailPageComponent);
    fixture.detectChanges();

    const httpTesting = TestBed.inject(HttpTestingController);
    const req = httpTesting.expectOne((r) => r.url.includes('/api/billing/my-invoices/6a85ff8f5cf638c2b82e1daf'));
    req.flush({ ...DETAIL_DTO, _id: '6a85ff8f5cf638c2b82e1daf' });

    // Bajo jest.useFakeTimers(), fixture.whenStable() se queda colgado (zona
    // espera macrotareas reales) — propagamos el valor del resource con
    // microtasks y un par de detectChanges.
    await Promise.resolve();
    await Promise.resolve();
    fixture.detectChanges();
    await Promise.resolve();
    fixture.detectChanges();
    return { fixture, httpTesting };
  }

  function inputFor(fixture: { nativeElement: HTMLElement }, placeholder: string): HTMLInputElement {
    return fixture.nativeElement.querySelector(`input[placeholder="${placeholder}"]`) as HTMLInputElement;
  }

  it('al pulsar Pagar ahora pide el número de tarjeta, titular, vencimiento y CVV', async () => {
    const { fixture } = await render();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Pagar ahora');

    ((fixture.nativeElement as HTMLElement).querySelector('.btn-pay') as HTMLButtonElement).click();
    fixture.detectChanges();

    const rendered = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(rendered).toContain('Número de tarjeta');
    expect(rendered).toContain('Titular');
    expect(rendered).toContain('Vencimiento');
    expect(rendered).toContain('CVV');
    expect(inputFor(fixture, '0000 0000 0000 0000')).not.toBeNull();
    expect(inputFor(fixture, 'MM/AA')).not.toBeNull();
    expect(inputFor(fixture, 'CVV')).not.toBeNull();
    fixture.destroy();
  });

  it('rechaza un número de tarjeta que no pasa Luhn y mantiene Continuar deshabilitado', async () => {
    const { fixture } = await render();
    ((fixture.nativeElement as HTMLElement).querySelector('.btn-pay') as HTMLButtonElement).click();
    fixture.detectChanges();

    inputFor(fixture, '0000 0000 0000 0000').value = '4242424242424241';
    inputFor(fixture, '0000 0000 0000 0000').dispatchEvent(new Event('input'));
    inputFor(fixture, 'Nombre del titular').value = 'ANA GARCIA';
    inputFor(fixture, 'Nombre del titular').dispatchEvent(new Event('input'));
    inputFor(fixture, 'MM/AA').value = '12/30';
    inputFor(fixture, 'MM/AA').dispatchEvent(new Event('input'));
    inputFor(fixture, 'CVV').value = '123';
    inputFor(fixture, 'CVV').dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const rendered = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(rendered).toContain('Número de tarjeta inválido');
    const cont = [...(fixture.nativeElement as HTMLElement).querySelectorAll('button')]
      .find((b) => (b.textContent ?? '').includes('Continuar'));
    expect(cont).toBeDefined();
    expect((cont as HTMLButtonElement).disabled).toBe(true);
    fixture.destroy();
  });

  it('con datos válidos muestra la tarjeta enmascarada en la confirmación', async () => {
    const { fixture } = await render();
    ((fixture.nativeElement as HTMLElement).querySelector('.btn-pay') as HTMLButtonElement).click();
    fixture.detectChanges();

    inputFor(fixture, '0000 0000 0000 0000').value = '4242424242424242';
    inputFor(fixture, '0000 0000 0000 0000').dispatchEvent(new Event('input'));
    inputFor(fixture, 'Nombre del titular').value = 'ANA GARCIA';
    inputFor(fixture, 'Nombre del titular').dispatchEvent(new Event('input'));
    inputFor(fixture, 'MM/AA').value = '12/30';
    inputFor(fixture, 'MM/AA').dispatchEvent(new Event('input'));
    inputFor(fixture, 'CVV').value = '123';
    inputFor(fixture, 'CVV').dispatchEvent(new Event('input'));
    fixture.detectChanges();

    const cont = [...(fixture.nativeElement as HTMLElement).querySelectorAll('button')]
      .find((b) => (b.textContent ?? '').includes('Continuar')) as HTMLButtonElement;
    expect(cont.disabled).toBe(false);
    cont.click();
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Procesando pago');

    jest.advanceTimersByTime(2000);
    fixture.detectChanges();

    const rendered = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(rendered).toContain('•••• 4242');
    expect(rendered).toContain('Confirmar pago');
    fixture.destroy();
  });

  it('al salir del campo (blur) el número se muestra 4242 **** **** 4242 y al re-focar vuelve completo', async () => {
    const { fixture } = await render();
    ((fixture.nativeElement as HTMLElement).querySelector('.btn-pay') as HTMLButtonElement).click();
    fixture.detectChanges();

    const numberInput = inputFor(fixture, '0000 0000 0000 0000');
    numberInput.value = '4242424242424242';
    numberInput.dispatchEvent(new Event('input'));
    fixture.detectChanges();

    // Blur: se enmascara el centro; la validación interna no cambia.
    numberInput.dispatchEvent(new Event('blur'));
    fixture.detectChanges();
    expect(numberInput.value).toBe('4242 **** **** 4242');

    // Focus: vuelve el número completo para editar.
    numberInput.dispatchEvent(new Event('focus'));
    fixture.detectChanges();
    expect(numberInput.value).toBe('4242 4242 4242 4242');
    fixture.destroy();
  });

  it('el enmascarado por blur no rompe la validación: Continuar sigue habilitado', async () => {
    const { fixture } = await render();
    ((fixture.nativeElement as HTMLElement).querySelector('.btn-pay') as HTMLButtonElement).click();
    fixture.detectChanges();

    const numberInput = inputFor(fixture, '0000 0000 0000 0000');
    numberInput.value = '4242424242424242';
    numberInput.dispatchEvent(new Event('input'));
    inputFor(fixture, 'Nombre del titular').value = 'ANA GARCIA';
    inputFor(fixture, 'Nombre del titular').dispatchEvent(new Event('input'));
    inputFor(fixture, 'MM/AA').value = '12/30';
    inputFor(fixture, 'MM/AA').dispatchEvent(new Event('input'));
    inputFor(fixture, 'CVV').value = '123';
    inputFor(fixture, 'CVV').dispatchEvent(new Event('input'));
    numberInput.dispatchEvent(new Event('blur'));
    fixture.detectChanges();

    expect(numberInput.value).toBe('4242 **** **** 4242');
    const cont = [...(fixture.nativeElement as HTMLElement).querySelectorAll('button')]
      .find((b) => (b.textContent ?? '').includes('Continuar')) as HTMLButtonElement;
    expect(cont.disabled).toBe(false);
    fixture.destroy();
  });
});
