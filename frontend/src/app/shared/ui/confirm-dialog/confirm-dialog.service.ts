import { Injectable, signal } from '@angular/core';
import { inject } from '@angular/core';

import { OperationModeService, type OperationMode } from '../../../core/services/operation-mode.service';

export interface ConfirmDialogInputConfig {
  /** Label mostrado sobre el campo (opcional). */
  label?: string;
  /** Placeholder del campo. */
  placeholder?: string;
  /** Si es true, el botón de confirmar queda deshabilitado hasta escribir algo. */
  required?: boolean;
  maxLength?: number;
  /** Valor inicial del campo. */
  initialValue?: string;
}

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
  /**
   * Campo de texto opcional (petición de motivo/nota). Solo lo usa
   * `openPrompt()`; `open()` no lo renderiza y sigue resolviendo boolean.
   */
  input?: ConfirmDialogInputConfig;
}

@Injectable({ providedIn: 'root' })
export class ConfirmDialogService {
  private readonly opMode = inject(OperationModeService);

  readonly isOpen = signal(false);
  readonly config = signal<ConfirmDialogConfig>({ title: '', message: '' });
  /** Valor actual del campo de texto cuando `config().input` está presente. */
  readonly inputValue = signal('');

  private resolveFn: ((result: boolean | string) => void) | null = null;
  /** Modo previo capturado al abrir un diálogo con `config.mode` — se restaura al cerrar. */
  private savedTransientRelease: (() => void) | null = null;

  /** Open the confirmation dialog. Returns a Promise that resolves to true (confirmed) or false (cancelled).
   * If a dialog is already open, it is cleanly dismissed first. */
  open(config: ConfirmDialogConfig): Promise<boolean> {
    // Cleanly dismiss any in-flight dialog to avoid orphaned promises
    this._close(false);

    this._applyTransientMode(config);

    return new Promise<boolean>((resolve) => {
      this.resolveFn = (result) => resolve(result === true);
      this.config.set({
        confirmLabel: 'Confirmar',
        cancelLabel: 'Cancelar',
        variant: 'danger',
        ...config,
      });
      this.inputValue.set(config.input?.initialValue ?? '');
      this.isOpen.set(true);
    });
  }

  /**
   * Abre el diálogo de confirmación con un campo de texto opcional.
   * Resuelve el valor escrito al confirmar, o `null` si se cancela.
   * (``open()`` mantiene su contrato `boolean` para no romper los ~30 usos
   * existentes; este método es el que permite capturar motivo/nota.)
   */
  openPrompt(config: ConfirmDialogConfig & { input: ConfirmDialogInputConfig }): Promise<string | null> {
    // Cleanly dismiss any in-flight dialog to avoid orphaned promises
    this._close(false);

    this._applyTransientMode(config);

    return new Promise<string | null>((resolve) => {
      this.resolveFn = (result) => resolve(typeof result === 'string' ? result : null);
      this.config.set({
        confirmLabel: 'Confirmar',
        cancelLabel: 'Cancelar',
        variant: 'danger',
        ...config,
      });
      this.inputValue.set(config.input.initialValue ?? '');
      this.isOpen.set(true);
    });
  }

  confirm(): void {
    const cfg = this.config();
    if (cfg.input) {
      this._close(this.inputValue());
    } else {
      this._close(true);
    }
  }

  cancel(): void {
    this._close(false);
  }

  private _applyTransientMode(config: ConfirmDialogConfig): void {
    // Si el diálogo declara un modo, mostrarlo en el nav mientras esté abierto.
    // Se captura el modo previo para restaurarlo al cerrar (ej. una página de
    // edición que abre un confirm de borrado vuelve a 'update' al terminar).
    this.savedTransientRelease = null;
    if (config.mode) {
      this.savedTransientRelease = this.opMode.setTransientMode(config.mode, config.modeDetail ?? '');
    }
  }

  private _close(result: boolean | string): void {
    // Quitar el overlay; el modo de la página vuelve automáticamente.
    this.savedTransientRelease?.();
    this.savedTransientRelease = null;
    this.isOpen.set(false);
    this.resolveFn?.(result);
    this.resolveFn = null;
  }
}
