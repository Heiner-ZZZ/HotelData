import { TestBed } from '@angular/core/testing';

import { MpEtlProgressBoxComponent } from './mp-etl-progress-box';
import type { Ga03ProgressInfo } from '../../models/monitoring.model';

/** Progreso mínimo del ETL GA03 para la caja. */
function makeProgress(overrides: Partial<Ga03ProgressInfo> = {}): Ga03ProgressInfo {
  return {
    preparationStatus: 'idle',
    preparationPercent: 0,
    preparationMessage: '',
    preparationLoaded: 0,
    preparationTarget: 300000,
    pipelineStatus: 'idle',
    pipelinePercent: 0,
    pipelineElapsedMs: 0,
    pipelineMessage: '',
    pipelineSections: [
      { key: 'extract', label: 'Extraer', complete: false },
      { key: 'load', label: 'Cargar a MongoDB', complete: false },
    ],
    pipelineTarget: 300000,
    isRunning: false,
    ...overrides,
  };
}

async function render(inputs: Record<string, unknown>) {
  await TestBed.configureTestingModule({
    imports: [MpEtlProgressBoxComponent],
  }).compileComponents();

  const fixture = TestBed.createComponent(MpEtlProgressBoxComponent);
  for (const [key, value] of Object.entries(inputs)) {
    fixture.componentRef.setInput(key, value);
  }
  fixture.detectChanges();
  return fixture;
}

describe('MpEtlProgressBoxComponent', () => {
  it('muestra los porcentajes en el encabezado y mantiene el cuerpo colapsado por defecto', async () => {
    const fixture = await render({
      progress: makeProgress({ preparationPercent: 40, pipelinePercent: 25 }),
      targetPocketbase: 300000,
      targetMongodb: 300000,
    });

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Progreso ETL');
    expect(text).toContain('Preparación: 40% | Pipeline: 25%');
    expect(text).not.toContain('Preparar fuente desde CSV');
  });

  it('expande el cuerpo al hacer clic en el encabezado y muestra los selectores y acciones', async () => {
    const fixture = await render({
      progress: makeProgress(),
      targetPocketbase: 300000,
      targetMongodb: 300000,
    });

    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Preparación');
    expect(text).toContain('Pipeline');
    expect(text).toContain('Preparar fuente desde CSV');
    expect(text).toContain('Ejecutar pipeline');
    expect(text).toContain('Limpiar evidencia');
    expect(text).toContain('Registros a PocketBase:');
    expect(text).toContain('Registros a MongoDB:');
  });

  it('muestra el estado running con % reales, pasos del pipeline y el botón de modo', async () => {
    const fixture = await render({
      progress: makeProgress({
        isRunning: true,
        preparationStatus: 'running',
        preparationLoaded: 120000,
        preparationTarget: 300000,
        preparationPercent: 40,
        pipelineStatus: 'running',
        pipelinePercent: 60,
        pipelineElapsedMs: 4500,
        pipelineSections: [
          { key: 'extract', label: 'Extraer', complete: true },
          { key: 'load', label: 'Cargar a MongoDB', complete: false },
        ],
      }),
      targetPocketbase: 300000,
      targetMongodb: 300000,
    });
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('120000');
    expect(text).toContain('/ 300000');
    expect(text).toContain('registros');
    expect(text).toContain('60% — 4500 ms');
    expect(text).toContain('Extraer');
    expect(text).toContain('completado');
    expect(text).toContain('Cargar a MongoDB');
    expect(text).toContain('Detener preparación');
    expect(text).toContain('Detener pipeline');
  });

  it('emite stopSeed y stopPipeline al pulsar los botones de detener', async () => {
    const fixture = await render({
      progress: makeProgress({
        isRunning: true,
        preparationStatus: 'running',
        pipelineStatus: 'running',
      }),
      targetPocketbase: 300000,
      targetMongodb: 300000,
    });
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    const component = fixture.componentInstance;
    const stopSeed = jest.spyOn(component.stopSeed, 'emit');
    const stopPipeline = jest.spyOn(component.stopPipeline, 'emit');

    const buttons = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button'));
    buttons.find(b => b.textContent?.includes('Detener preparación'))!.click();
    fixture.detectChanges();
    expect(stopSeed).toHaveBeenCalled();

    buttons.find(b => b.textContent?.includes('Detener pipeline'))!.click();
    fixture.detectChanges();
    expect(stopPipeline).toHaveBeenCalled();
  });

  it('emite las acciones seed, validate, pipeline y clearEvidence', async () => {
    const fixture = await render({
      progress: makeProgress(),
      targetPocketbase: 300000,
      targetMongodb: 300000,
    });
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    const component = fixture.componentInstance;
    const seed = jest.spyOn(component.seed, 'emit');
    const validate = jest.spyOn(component.validate, 'emit');
    const pipeline = jest.spyOn(component.pipeline, 'emit');
    const clearEvidence = jest.spyOn(component.clearEvidence, 'emit');

    const buttons = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button'));
    buttons.find(b => b.textContent?.includes('Preparar fuente desde CSV'))!.click();
    buttons.find(b => b.textContent?.includes('Validar dataset'))!.click();
    buttons.find(b => b.textContent?.includes('Ejecutar pipeline'))!.click();
    buttons.find(b => b.textContent?.includes('Limpiar evidencia'))!.click();
    fixture.detectChanges();

    expect(seed).toHaveBeenCalled();
    expect(validate).toHaveBeenCalled();
    expect(pipeline).toHaveBeenCalled();
    expect(clearEvidence).toHaveBeenCalled();
  });

  it('emite los nuevos targets al cambiar los selectores', async () => {
    const fixture = await render({
      progress: makeProgress(),
      targetPocketbase: 300000,
      targetMongodb: 300000,
    });
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    const component = fixture.componentInstance;
    const pbChange = jest.spyOn(component.targetPocketbaseChange, 'emit');
    const mongoChange = jest.spyOn(component.targetMongodbChange, 'emit');

    const pbSelect = (fixture.nativeElement as HTMLElement).querySelector<HTMLSelectElement>('#targetPbSelect')!;
    pbSelect.value = '400000';
    pbSelect.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(pbChange).toHaveBeenCalledWith(400000);

    const mongoSelect = (fixture.nativeElement as HTMLElement).querySelector<HTMLSelectElement>('#targetMongoSelect')!;
    mongoSelect.value = '500000';
    mongoSelect.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(mongoChange).toHaveBeenCalledWith(500000);
  });

  it('alterna el modo incremental y refleja la etiqueta correspondiente', async () => {
    const fixture = await render({
      progress: makeProgress(),
      targetPocketbase: 300000,
      targetMongodb: 300000,
      incrementalMode: false,
    });
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Completo');

    const component = fixture.componentInstance;
    const toggle = jest.spyOn(component.incrementalModeChange, 'emit');
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.mode-toggle')!.click();
    fixture.detectChanges();
    expect(toggle).toHaveBeenCalled();

    fixture.componentRef.setInput('incrementalMode', true);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Incremental');
  });

  it('deshabilita las acciones mientras actionBusy está activo', async () => {
    const fixture = await render({
      progress: makeProgress(),
      targetPocketbase: 300000,
      targetMongodb: 300000,
      actionBusy: true,
    });
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    const actionButtons = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll<HTMLButtonElement>('button.action-btn'));
    expect(actionButtons.length).toBeGreaterThan(0);
    expect(actionButtons.every(b => b.hasAttribute('disabled'))).toBe(true);
  });
});