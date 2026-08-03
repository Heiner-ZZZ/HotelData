import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';

import { OperationModeService } from '../../../core/services/operation-mode.service';

/**
 * Chip de modo CRUD para el nav superior. Muestra un cuadrito de color
 * (según la gravedad del modo actual) + label, con tooltip descriptivo.
 *
 * Uso en cualquier shell que tenga un header:
 *   <app-operation-mode-indicator />
 */
@Component({
  selector: 'app-operation-mode-indicator',
  imports: [],
  templateUrl: './operation-mode-indicator.html',
  styleUrl: './operation-mode-indicator.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OperationModeIndicatorComponent {
  private readonly operationMode = inject(OperationModeService);

  readonly mode = this.operationMode.mode;
  readonly info = this.operationMode.info;
  readonly detail = this.operationMode.detail;

  /** Clase CSS para el chip según el modo (read/insert/update/delete). */
  readonly chipClass = computed(() => `op-chip op-chip--${this.info().mode}`);

  /** Tooltip: label + detalle + descripción. */
  readonly tooltip = computed(() => {
    const i = this.info();
    const detail = this.detail();
    const parts = [i.label];
    if (detail) parts.push(`· ${detail}`);
    parts.push(`— ${i.description}`);
    return parts.join(' ');
  });
}
