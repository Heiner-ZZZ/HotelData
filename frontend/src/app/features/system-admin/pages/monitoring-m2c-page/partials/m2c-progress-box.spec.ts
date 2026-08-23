import { TestBed } from '@angular/core/testing';

import { M2cProgressBoxComponent } from './m2c-progress-box';
import type { M2cProgressDto } from '../../../models/monitoring-m2c.dto';

/** Progreso mínimo del pipeline M2C para la caja. */
function makeProgress(overrides: Partial<M2cProgressDto> = {}): M2cProgressDto {
  return {
    exists: true,
    path: '',
    status: 'pending',
    section: '',
    percent: 0,
    elapsed_ms: 0,
    message: 'Sin corrida en curso',
    detail: {},
    updated_at: '',
    sections: {},
    is_running: false,
    clickhouse_database: 'hoteldata_analytics',
    tables: [],
    ...overrides,
  };
}

async function render(inputs: Record<string, unknown>) {
  await TestBed.configureTestingModule({
    imports: [M2cProgressBoxComponent],
  }).compileComponents();

  const fixture = TestBed.createComponent(M2cProgressBoxComponent);
  for (const [key, value] of Object.entries(inputs)) {
    fixture.componentRef.setInput(key, value);
  }
  fixture.detectChanges();
  return fixture;
}

describe('M2cProgressBoxComponent', () => {
  it('muestra los KPIs en el encabezado y mantiene el cuerpo colapsado por defecto', async () => {
    const fixture = await render({
      progress: makeProgress({ percent: 40, message: 'Extrayendo desde MongoDB' }),
    });

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('ETL pipeline progress');
    expect(text).toContain('Extrayendo desde MongoDB (40%)');
    expect(text).not.toContain('Run pipeline');
  });

  it('expande el cuerpo al hacer clic en el encabezado y muestra barra, meta y pasos', async () => {
    const fixture = await render({
      progress: makeProgress({
        percent: 40,
        elapsed_ms: 1200,
        status: 'running',
        sections: {
          extract_mongo: { label: 'Extraer MongoDB', complete: true },
          transform: { label: 'Transformar', complete: false },
        },
      }),
    });
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('40%');
    expect(text).toContain('1200 ms');
    expect(text).toContain('Extraer MongoDB');
    expect(text).toContain('Transformar');
    expect(text).toContain('Run pipeline');
  });

  it('marca los pasos completados y pendientes según las secciones', async () => {
    const fixture = await render({
      progress: makeProgress({
        is_running: true,
        status: 'running',
        percent: 60,
        sections: {
          validate_config: { label: 'Validar config', complete: true },
          extract_mongo: { label: 'Extraer MongoDB', complete: true },
          transform: { label: 'Transformar', complete: false },
        },
      }),
    });
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    const done = fixture.nativeElement.querySelectorAll('.step-done');
    const pending = fixture.nativeElement.querySelectorAll('.step-pending');
    expect(done.length).toBe(2);
    expect(pending.length).toBe(1);
  });

  it('emite run cuando no hay corrida en curso', async () => {
    const fixture = await render({
      progress: makeProgress({ is_running: false }),
    });
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    const component = fixture.componentInstance;
    const run = jest.spyOn(component.run, 'emit');
    const buttons = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button'));
    buttons.find(b => b.textContent?.includes('Run pipeline'))!.click();
    expect(run).toHaveBeenCalled();
  });

  it('muestra el botón Stop solo mientras el pipeline corre y emite stop', async () => {
    const fixture = await render({
      progress: makeProgress({ is_running: true, status: 'running' }),
    });
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    const component = fixture.componentInstance;
    const stop = jest.spyOn(component.stop, 'emit');

    const buttons = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button'));
    expect(buttons.some(b => b.textContent?.includes('Stop'))).toBe(true);

    buttons.find(b => b.textContent?.includes('Stop'))!.click();
    expect(stop).toHaveBeenCalled();
  });

  it('oculta el botón Stop cuando no hay corrida en curso', async () => {
    const fixture = await render({ progress: makeProgress({ is_running: false }) });
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).not.toContain('Stop');
  });

  it('deshabilita Run y Stop mientras actionBusy está activo', async () => {
    const fixture = await render({
      progress: makeProgress({ is_running: true }),
      actionBusy: true,
    });
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    const actionButtons = Array.from(
      (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLButtonElement>('.action-btn'),
    );
    expect(actionButtons.length).toBeGreaterThan(0);
    expect(actionButtons.every(b => b.hasAttribute('disabled'))).toBe(true);
  });
});
