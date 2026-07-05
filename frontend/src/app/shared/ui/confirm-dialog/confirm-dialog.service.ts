import { Injectable, signal } from '@angular/core';

export interface ConfirmDialogConfig {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'default';
  /** Optional structured details shown below the message (e.g. key-value lines). */
  details?: string[];
}

@Injectable({ providedIn: 'root' })
export class ConfirmDialogService {
  readonly isOpen = signal(false);
  readonly config = signal<ConfirmDialogConfig>({ title: '', message: '' });

  private resolveFn: ((result: boolean) => void) | null = null;

  /** Open the confirmation dialog. Returns a Promise that resolves to true (confirmed) or false (cancelled).
   * If a dialog is already open, it is cleanly dismissed first. */
  open(config: ConfirmDialogConfig): Promise<boolean> {
    // Cleanly dismiss any in-flight dialog to avoid orphaned promises
    this._close(false);
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
    this.isOpen.set(false);
    this.resolveFn?.(result);
    this.resolveFn = null;
  }
}
