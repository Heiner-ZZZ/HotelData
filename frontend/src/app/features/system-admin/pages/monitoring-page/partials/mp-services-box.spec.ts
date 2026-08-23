import { TestBed } from '@angular/core/testing';

import { MpServicesBoxComponent } from './mp-services-box';
import type { MonitoringServicesViewModel } from '../../models/monitoring.model';

function makeServices(overrides: Partial<MonitoringServicesViewModel> = {}): MonitoringServicesViewModel {
  return {
    services: [
      { label: 'PocketBase', icon: 'db', value: 'ready', description: 'Colección hotel_reservation_events_03', tone: 'success' },
      { label: 'MongoDB', icon: 'db', value: 'ready', description: 'Base hoteldata', tone: 'warning' },
      { label: 'Artifacts', icon: 'doc', value: 'parcial', description: 'Sin JSONL', tone: 'error' },
      { label: 'Extra', icon: 'list', value: 'n/d', description: 'Sin dato', tone: 'muted' },
    ],
    configInfo: {
      taskNumber: 'GA03',
      targetRecords: 300000,
      targetRecordsPb: 300000,
      targetRecordsMongo: 300000,
      pbCollection: 'hotel_reservation_events_03',
      sourceCsvExists: false,
      sourceCsv: 'reservas_ga03.csv',
    },
    ...overrides,
  };
}

async function render(inputs: Record<string, unknown>) {
  TestBed.resetTestingModule();
  await TestBed.configureTestingModule({
    imports: [MpServicesBoxComponent],
  }).compileComponents();

  const fixture = TestBed.createComponent(MpServicesBoxComponent);
  for (const [key, value] of Object.entries(inputs)) {
    fixture.componentRef.setInput(key, value);
  }
  fixture.detectChanges();
  return fixture;
}

describe('MpServicesBoxComponent — Estado de servicios', () => {
  it('muestra el encabezado con la config y mantiene el cuerpo colapsado por defecto', async () => {
    const fixture = await render({ services: makeServices() });
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Estado de servicios');
    expect(text).toContain('GA03');
    expect(text).toContain('hotel_reservation_events_03');
    expect(fixture.nativeElement.querySelector('.service-card')).toBeNull();
  });

  it('expande el cuerpo al hacer clic en el encabezado y muestra las cards de servicios', async () => {
    const fixture = await render({ services: makeServices() });
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    const cards = fixture.nativeElement.querySelectorAll('.service-card');
    expect(cards.length).toBe(4);
    expect((fixture.nativeElement.textContent as string)).toContain('PocketBase');
    expect((fixture.nativeElement.textContent as string)).toContain('MongoDB');
    expect((fixture.nativeElement.textContent as string)).toContain('Sin JSONL');
  });

  it('traduce cada tone a su badge Disponible/Atención/Error/N/D', async () => {
    const fixture = await render({ services: makeServices() });
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Disponible');
    expect(text).toContain('Atención');
    expect(text).toContain('Error');
    expect(text).toContain('N/D');
  });

  it('muestra la fila de config con el CSV fuente y su badge de estado', async () => {
    const fixture = await render({ services: makeServices() });
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('reservas_ga03.csv');
    expect(text).toContain('No encontrado');
  });
});
