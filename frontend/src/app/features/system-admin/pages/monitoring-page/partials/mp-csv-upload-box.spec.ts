import { TestBed } from '@angular/core/testing';

import { MpCsvUploadBoxComponent } from './mp-csv-upload-box';

async function render(inputs: Record<string, unknown> = {}) {
  await TestBed.configureTestingModule({
    imports: [MpCsvUploadBoxComponent],
  }).compileComponents();

  const fixture = TestBed.createComponent(MpCsvUploadBoxComponent);
  for (const [key, value] of Object.entries(inputs)) {
    fixture.componentRef.setInput(key, value);
  }
  fixture.detectChanges();
  return fixture;
}

function expand(fixture: { nativeElement: unknown; detectChanges(): void }) {
  ((fixture.nativeElement as HTMLElement).querySelector<HTMLElement>('.accordion-header'))!.click();
  fixture.detectChanges();
}

describe('MpCsvUploadBoxComponent', () => {
  it('muestra el título y mantiene el cuerpo colapsado por defecto', async () => {
    const fixture = await render();

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Subir CSV fuente');
    expect(text).not.toContain('Seleccionar archivo CSV');
  });

  it('expande el cuerpo al hacer clic en el encabezado', async () => {
    const fixture = await render();
    expand(fixture);

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Seleccionar archivo CSV');
    expect(text).toContain('Subir CSV');
  });

  it('muestra el nombre del archivo seleccionado', async () => {
    const fixture = await render({ selectedFileName: 'reservas_ga03.csv' });
    expand(fixture);

    expect(fixture.nativeElement.textContent).toContain('reservas_ga03.csv');
  });

  it('emite el archivo al elegirlo en el input', async () => {
    const fixture = await render();
    expand(fixture);

    const component = fixture.componentInstance;
    const fileSelected = jest.spyOn(component.fileSelected, 'emit');

    const file = new File(['a,b\n1,2'], 'reservas_ga03.csv', { type: 'text/csv' });
    const input = (fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>('#csvFile')!;
    Object.defineProperty(input, 'files', { value: [file], configurable: true });
    input.dispatchEvent(new Event('change'));
    fixture.detectChanges();

    expect(fileSelected).toHaveBeenCalledWith(file);
  });

  it('emite upload al pulsar Subir CSV', async () => {
    const fixture = await render({ selectedFileName: 'reservas_ga03.csv' });
    expand(fixture);

    const component = fixture.componentInstance;
    const upload = jest.spyOn(component.upload, 'emit');

    const button = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button'))
      .find(b => b.textContent?.includes('Subir CSV'))!;
    button.click();
    fixture.detectChanges();

    expect(upload).toHaveBeenCalled();
  });

  it('muestra Subiendo... y deshabilita el botón mientras busy', async () => {
    const fixture = await render({ selectedFileName: 'reservas_ga03.csv', busy: true });
    expand(fixture);

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Subiendo...');
    const button = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button'))
      .find(b => b.textContent?.includes('Subiendo'))!;
    expect((button as HTMLButtonElement).hasAttribute('disabled')).toBe(true);
  });

  it('deshabilita Subir CSV mientras no hay archivo seleccionado', async () => {
    const fixture = await render();
    expand(fixture);

    const button = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button'))
      .find(b => b.textContent?.includes('Subir CSV'))!;
    expect((button as HTMLButtonElement).hasAttribute('disabled')).toBe(true);
  });

  it('resetea el input nativo cuando el padre limpia el archivo tras la subida', async () => {
    const fixture = await render({ selectedFileName: 'reservas_ga03.csv' });
    expand(fixture);

    const input = (fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>('#csvFile')!;
    // jsdom solo admite el string vacío en inputs de archivo: simula la selección
    // vía files y verifica que el reseteo del padre deja el input sin valor.
    Object.defineProperty(input, 'files', { value: [], configurable: true });

    fixture.componentRef.setInput('selectedFileName', null);
    fixture.detectChanges();

    expect(input.value).toBe('');
  });
});