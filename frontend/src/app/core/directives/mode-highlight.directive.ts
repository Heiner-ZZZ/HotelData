import { Directive, ElementRef, effect, inject } from '@angular/core';

import { OperationModeService } from '../services/operation-mode.service';

/**
 * Resalta el panel que contiene un form según el modo CRUD activo del nav.
 * Añade la clase `mode-active` cuando el modo es de escritura (insert/update/
 * delete) y expone `--op-color` con el color del mode-indicator (read=verde,
 * insert=ámbar, update=naranja, delete=rojo).
 *
 * El look visual (borde fino + halo con el color) vive en
 * `styles/_scss-mode-highlight.scss`; este directive solo declara el estado.
 *
 * Uso en cualquier panel de form del sistema:
 *   <section class="surface-card data-panel" appModeHighlight> ... </section>
 */
@Directive({
  selector: '[appModeHighlight]',
  standalone: true,
})
export class ModeHighlightDirective {
  private readonly el = inject(ElementRef<HTMLElement>);
  private readonly opMode = inject(OperationModeService);

  constructor() {
    effect(() => {
      const info = this.opMode.info();
      const writing = info.mode !== 'read';
      this.el.nativeElement.classList.toggle('mode-active', writing);
      this.el.nativeElement.style.setProperty('--op-color', info.color);
    });
  }
}
