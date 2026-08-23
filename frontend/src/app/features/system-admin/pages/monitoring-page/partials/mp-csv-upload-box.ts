import { ChangeDetectionStrategy, Component, effect, ElementRef, input, output, signal, viewChild } from '@angular/core';

/**
 * Caja "Subir CSV fuente" del monitoreo GA03.
 *
 * Componente OnPush aislado: su vista solo se re-renderiza por su propio estado
 * (archivo seleccionado, subida en curso). El polling del ETL no la toca, de
 * modo que la subida de un CSV a PocketBase no re-renderiza el resto de la
 * interfaz ni viceversa.
 */
@Component({
  selector: 'app-mp-csv-upload-box',
  templateUrl: './mp-csv-upload-box.html',
  styleUrl: './mp-csv-upload-box.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MpCsvUploadBoxComponent {
  /** Subida en curso (deshabilita el input y el botón). */
  readonly busy = input(false);
  /** Nombre del archivo elegido; el padre lo limpia tras una subida exitosa. */
  readonly selectedFileName = input<string | null>(null);

  readonly fileSelected = output<File>();
  readonly upload = output<void>();

  readonly open = signal(false);

  private readonly fileInput = viewChild<ElementRef<HTMLInputElement>>('fileInput');

  constructor() {
    // Cuando el padre confirma la subida y limpia el archivo, resetea también el
    // input nativo para que volver a elegir el mismo CSV sí dispare (change).
    effect(() => {
      if (!this.selectedFileName()) {
        const native = this.fileInput()?.nativeElement;
        if (native) native.value = '';
      }
    });
  }

  toggleOpen() {
    this.open.update(v => !v);
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files?.length) {
      this.fileSelected.emit(input.files[0]);
    }
  }
}