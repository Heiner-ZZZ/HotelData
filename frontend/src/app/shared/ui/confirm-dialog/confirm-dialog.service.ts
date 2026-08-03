import { Injectable, signal } from '@angular/core';
import { inject } from '@angular/core';

import { OperationModeService, type OperationMode } from '../../../core/services/operation-mode.service';

export interface ConfirmDialogConfig {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'default';
  /** Optional structured details shown below the message (e.g. key-value lines). */
  details?: string[];
  /**
   * Modo CRUD a mostrar en el nav mientras el diálogo está abierto.
   * Al cerrar (confirmar o cancelar) se restaura el modo previo.
   * Usado por flujos destructivos: `mode: 'delete'`.
   */
  mode?: OperationMode;
  /** Detalle opcional para el tooltip del chip de modo (ej. "Tarea — Hab. 101"). */
  modeDetail?: string;
}

@Injectable({ providedIn: 'root' })
export class ConfirmDialogService {
  private readonly opMode = inject(OperationModeService);

  readonly isOpen = signal(false);
  readonly config = signal<ConfirmDialogConfig>({ title: '', message: '' });

  private resolveFn: ((result: boolean) => void) | null = null;
  /** Modo previo capturado al abrir un diálogo con `config.mode` — se restaura al cerrar. */
  private savedMode: OperationMode | null = null;
  private savedDetail = '';

  /** Open the confirmation dialog. Returns a Promise that resolves to true (confirmed) or false (cancelled).
   * If a dialog is already open, it is cleanly dismissed first. */
  open(config: ConfirmDialogConfig): Promise<boolean> {
    // Cleanly dismiss any in-flight dialog to avoid orphaned promises
    this._close(false);

    // Si el diálogo declara un modo, mostrarlo en el nav mientras esté abierto.
    // Se captura el modo previo para restaurarlo al cerrar (ej. una página de
    // edición que abre un confirm de borrado vuelve a 'update' al terminar).
    this.savedMode = null;
    this.savedDetail = '';
    if (config.mode) {
      this.savedMode = this.opMode.mode();
      this.savedDetail = this.opMode.detail();
      this.opMode.setMode(config.mode, config.modeDetail ?? '');
    }

    return new Promise<boolean>((resolve) => {
      this.resolveFn = resolve;
      this.config.set({
        confirmLabel: 'Confirmar',
        cancelLabel: 'Cancelar',
        variant: 'danger',
        ...config,
      });
      this.isOpen.set(true);
    });
  }

  confirm(): void {
    this._close(true);
  }

  cancel(): void {
    this._close(false);
  }

  private _close(result: boolean): void {
    // Restaurar el modo CRUD previo que quedó capturado al abrir (si aplica).
    if (this.savedMode !== null) {
      this.opMode.setMode(this.savedMode, this.savedDetail);
      this.savedMode = null;
      this.savedDetail = '';
    }
    this.isOpen.set(false);
    this.resolveFn?.(result);
    this.resolveFn = null;
  }
}
