import { TestBed } from '@angular/core/testing';

import { MpExecutionBoxComponent } from './mp-execution-box';
import type { MonitoringViewModel } from '../../models/monitoring.model';

type Execution = NonNullable<MonitoringViewModel['execution']>;

function makeExecution(overrides: Partial<Execution> = {}): Execution {
  return {
    available: true,
    executionId: 'ga03_2026_08_20_1000',
    executedAt: '20/08/2026, 10:00',
    status: 'success',
    validRecords: 250000,
    rejectedRecords: 12,
    sourceRows: 250012,
    ...overrides,
  };
}

async function render(inputs: Record<string, unknown>) {
  TestBed.resetTestingModule();
  await TestBed.configureTestingModule({
    imports: [MpExecutionBoxComponent],
  }).compileComponents();

  const fixture = TestBed.createComponent(MpExecutionBoxComponent);
  for (const [key, value] of Object.entries(inputs)) {
    fixture.componentRef.setInput(key, value);
  }
  fixture.detectChanges();
  return fixture;
}

describe('MpExecutionBoxComponent — Última ejecución', () => {
  it('sin ejecución no renderiza nada (ni el acordeón)', async () => {
    const fixture = await render({ execution: null });
    expect(fixture.nativeElement.querySelector('.accordion-section')).toBeNull();
    expect(fixture.nativeElement.textContent).not.toContain('Última ejecución');
  });

  it('muestra el encabezado y mantiene el cuerpo colapsado por defecto (el estado vive en el cuerpo)', async () => {
    const fixture = await render({ execution: makeExecution() });
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Última ejecución');
    expect(text).not.toContain('success');
    expect(fixture.nativeElement.querySelector('.exec-item')).toBeNull();
  });

  it('expande el cuerpo y muestra las métricas de la corrida', async () => {
    const fixture = await render({ execution: makeExecution() });
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('ga03_2026_08_20_1000');
    expect(text).toContain('20/08/2026, 10:00');
    expect(text).toContain('250000');
    expect(text).toContain('12');
    expect(text).toContain('250012');
  });

  it('muestra el estado failed al expandir el cuerpo', async () => {
    const fixture = await render({ execution: makeExecution({ status: 'failed' }) });
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('failed');
  });
});
