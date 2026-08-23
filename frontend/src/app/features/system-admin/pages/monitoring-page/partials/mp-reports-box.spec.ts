import { TestBed } from '@angular/core/testing';

import { MpReportsBoxComponent } from './mp-reports-box';
import type { ReportItem } from '../../models/monitoring.model';

function makeReports(): ReportItem[] {
  return [
    { name: 'resumen', label: 'Resumen del proceso', exists: true, path: '/data/evidence/resumen.md' },
    { name: 'kpis', label: 'KPIs del pipeline', exists: false, path: '/data/evidence/kpis.json' },
  ];
}

async function render(inputs: Record<string, unknown>) {
  TestBed.resetTestingModule();
  await TestBed.configureTestingModule({
    imports: [MpReportsBoxComponent],
  }).compileComponents();

  const fixture = TestBed.createComponent(MpReportsBoxComponent);
  for (const [key, value] of Object.entries(inputs)) {
    fixture.componentRef.setInput(key, value);
  }
  fixture.detectChanges();
  return fixture;
}

describe('MpReportsBoxComponent — Reportes', () => {
  it('muestra el encabezado y mantiene el cuerpo colapsado por defecto', async () => {
    const fixture = await render({ reports: makeReports() });
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Reportes');
    expect(text).toContain('Evidencia local del proceso ETL GA03.');
    expect(fixture.nativeElement.querySelector('tbody')).toBeNull();
  });

  it('expande el cuerpo y lista cada reporte con estado y ruta', async () => {
    const fixture = await render({ reports: makeReports() });
    (fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header')!.click();
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Resumen del proceso');
    expect(text).toContain('KPIs del pipeline');
    expect(text).toContain('Disponible');
    expect(text).toContain('Pendiente');
    expect(text).toContain('/data/evidence/resumen.md');
    expect(text).toContain('/data/evidence/kpis.json');
  });
});
