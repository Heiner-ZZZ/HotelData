import { computed, DestroyRef, inject, Injectable, signal } from '@angular/core';
import { NavigationStart, Router } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { filter } from 'rxjs';

/**
 * Modo CRUD actual de la interfaz. Cada página/componente lo declara
 * explícitamente (patrón manual por página) y el nav superior lo muestra
 * como un chip de color con la gravedad correspondiente.
 *
 * Escala de gravedad (de menor a mayor):
 *   read   → verde  (solo lectura, seguro)
 *   insert → ámbar  (registra información NUEVA)
 *   update → naranja (sobrescribe información EXISTENTE — más grave que
 *            insertar porque el estado anterior solo queda en el log)
 *   delete → rojo   (borrado, aunque sea lógico)
 */
export type OperationMode = 'read' | 'insert' | 'update' | 'delete';

export interface OperationModeInfo {
  mode: OperationMode;
  /** Label corto mostrado en el chip del nav. */
  label: string;
  /** Texto completo para el tooltip. */
  description: string;
  /** Token CSS del color del chip. */
  color: string;
  /** Orden de gravedad (para estilos/animaciones). */
  severity: number;
}

const MODE_INFO: Record<OperationMode, Omit<OperationModeInfo, 'mode'>> = {
  read: {
    label: 'Solo lectura',
    description: 'Estás viendo información sin modificar nada.',
    color: 'var(--success)',
    severity: 0,
  },
  insert: {
    label: 'Creando',
    description: 'Estás registrando información nueva en el sistema.',
    color: 'var(--warning)',
    severity: 1,
  },
  update: {
    label: 'Editando',
    description: 'Estás modificando información existente. El estado anterior queda solo en el log.',
    color: 'color-mix(in srgb, var(--warning) 45%, var(--danger) 55%)',
    severity: 2,
  },
  delete: {
    label: 'Eliminando',
    description: 'Estás eliminando información. Es un borrado lógico, pero afecta de forma permanente.',
    color: 'var(--danger)',
    severity: 3,
  },
};

@Injectable({
  providedIn: 'root',
})
export class OperationModeService {
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  private readonly modeSignal = signal<OperationMode>('read');
  private readonly detailSignal = signal('');

  /** Modo CRUD actual (por defecto `read`). */
  readonly mode = this.modeSignal.asReadonly();
  /** Detalle opcional (ej. "Tarifa X" / "Reserva #BK-…") para el tooltip. */
  readonly detail = this.detailSignal.asReadonly();

  /** Metadatos completos (label, color, gravedad) del modo actual. */
  readonly info = computed<OperationModeInfo>(() => {
    const base = MODE_INFO[this.modeSignal()];
    return { mode: this.modeSignal(), ...base };
  });

  constructor() {
    // Al INICIAR la navegación se vuelve al modo lectura por defecto. El
    // reset en NavigationStart (y no NavigationEnd) garantiza que el
    // constructor de la página nueva —que corre durante el change detection,
    // después de los eventos del router— gane siempre con su setMode().
    this.router.events
      .pipe(
        filter((e): e is NavigationStart => e instanceof NavigationStart),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(() => {
        this.modeSignal.set('read');
        this.detailSignal.set('');
      });
  }

  /** Declara el modo CRUD actual de la página. */
  setMode(mode: OperationMode, detail = ''): void {
    this.modeSignal.set(mode);
    this.detailSignal.set(detail);
  }

  /** Vuelve al modo lectura (por defecto). Llamar al desmontar la página. */
  reset(): void {
    this.modeSignal.set('read');
    this.detailSignal.set('');
  }
}
