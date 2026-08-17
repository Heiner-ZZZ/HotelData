import { HttpClient } from '@angular/common/http';
import { httpResource } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  HostListener,
  inject,
  input,
  output,
} from '@angular/core';
import { getErrorMessage } from '../../utils/http-error.util';
import { API_CONFIG } from '../../../core/api/api.config';

interface LegalSectionDto {
  readonly heading: string;
  readonly body: string;
}

export interface LegalDocumentDto {
  readonly doc_type: string;
  readonly version: number;
  readonly title: string;
  readonly effective_date: string | null;
  readonly sections: readonly LegalSectionDto[];
}

/** Labels públicos por doc_type (espejo del backend legal.service.DOC_TYPE_LABELS). */
export const TERMS_LABELS: Record<string, string> = {
  terms_guest: 'Términos y Condiciones',
  terms_hotel_partner: 'Términos y Condiciones para Anfitriones',
  privacy_policy: 'Política de Privacidad',
};

/**
 * Modal de Términos y Condiciones / Política de Privacidad.
 *
 * El texto se carga SIEMPRE del backend (`GET /api/public/legal`) — nunca se
 * hardcodea en el frontend. El padre controla la visibilidad (`open`) y recibe
 * el `close`; el documento activo (título, versión, fecha y secciones) queda
 * expuesto vía `documentResource` para que el flujo de registro pueda estampar
 * la versión aceptada en el payload.
 */
@Component({
  selector: 'app-terms-dialog',
  standalone: true,
  imports: [],
  templateUrl: './terms-dialog.html',
  styleUrl: './terms-dialog.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TermsDialogComponent {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  /** Doc type a mostrar (terms_guest | terms_hotel_partner | privacy_policy). */
  readonly docType = input.required<string>();
  /** Abre/cierra el modal desde el padre. */
  readonly open = input(false);
  /** Emite al cerrar (botón, Escape o click en el fondo). */
  readonly close = output<void>();

  readonly documentResource = httpResource<LegalDocumentDto | null>(
    () => {
      const docType = this.docType();
      const isOpen = this.open();
      if (!isOpen) return undefined;
      return `${this.apiConfig.baseUrl}/public/legal?doc_type=${encodeURIComponent(docType)}`;
    },
    {
      parse: (dto) => {
        const raw = dto as LegalDocumentDto | null;
        if (!raw?.sections?.length) return null;
        return raw;
      },
    },
  );

  /** Acceso seguro al valor: en estado de error, ``resource.value()`` re-lanza
   *  un ``ResourceValueError`` — lo enmascaramos para que el template pueda
   *  renderizar el estado de error sin crashear el cambio de detección. */
  readonly document = computed(() => {
    try {
      return this.documentResource.value();
    } catch {
      return null;
    }
  });

  readonly title = this.document;
  readonly isLoading = this.documentResource.isLoading;
  readonly error = this.documentResource.error;

  /** Mensaje legible del error (para el estado vacío). */
  readonly errorMessage = (): string =>
    getErrorMessage(this.error()) || 'No pudimos cargar el documento legal. Intenta de nuevo.';

  /** Etiqueta del doc type para el header (fallback si el backend no manda title). */
  readonly typeLabel = (): string =>
    TERMS_LABELS[this.docType()] ?? 'Documento legal';

  /** Fecha efectiva formateada local (ej. "15 Ago 2026"). */
  readonly effectiveDateLabel = (): string => {
    const raw = this.document()?.effective_date;
    if (!raw) return '';
    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleDateString('es-ES', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.open()) this.close.emit();
  }

  /** Reintenta la carga tras un error. */
  retry(): void {
    this.documentResource.reload();
  }
}
