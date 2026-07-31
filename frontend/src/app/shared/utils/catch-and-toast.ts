import { isDevMode } from '@angular/core';
import { toast } from '../../core/toast/toast.service';

/**
 * Extracts a human-readable message from any thrown value (Error, string,
 * HttpErrorResponse, duck-typed object). HttpErrorResponse carries the
 * server's `detail` at `err.error.detail`; this helper digs it out so
 * devs see meaningful toasts instead of generic "Http failure response".
 */
export function toErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof Error) return err.message;
  if (typeof err === 'string') return err;
  if (typeof err === 'object' && err !== null) {
    const e = err as {
      error?: { detail?: unknown; message?: unknown };
      message?: unknown;
      status?: unknown;
    };
    if (typeof e.error?.detail === 'string') return e.error.detail;
    if (typeof e.error?.message === 'string') return e.error.message;
    if (typeof e.message === 'string') return e.message;
    if (typeof e.status === 'number') return `HTTP ${e.status}`;
  }
  return fallback;
}

/**
 * Centralized catch handler factory. Use at any silent-fail `.catch()` or
 * `catch (err) {}` site to ensure dev visibility (console.error in dev
 * mode) AND a global red/amber toast the dev or end-user can read.
 *
 * Behavior:
 *   - Always: emits a toast containing the readable error message so the
 *     problem is visible at the top of the viewport — fixes the user's
 *     "errors don't show in console" complaint on /hotels/1.
 *   - Dev only: console.error with the raw error + context prefix for
 *     full triage (stack, status, response body).
 *   - Returns the caller's `fallback` value so Promise/observable chains
 *     resolve deterministically (existing flow control preserved).
 *
 * Use `catchAndToastError` for genuine failure paths (HTTP, validation,
 * authorization). Use `catchAndToastWarning` for graceful-degradation
 * paths (localStorage misses, date-parse fallbacks) where a red toast
 * would be alarmist.
 */
export function catchAndToastError<T>(context: string, fallback: T) {
  return (err: unknown): T => {
    const message = toErrorMessage(err, `Error en ${context}`);
    if (isDevMode()) console.error(`[${context}] failed`, err);
    toast(`${context}: ${message}`, 'error', 6000);
    return fallback;
  };
}

export function catchAndToastWarning<T>(context: string, fallback: T) {
  return (err: unknown): T => {
    const message = toErrorMessage(err, `Error en ${context}`);
    if (isDevMode()) console.error(`[${context}] failed`, err);
    toast(`${context}: ${message}`, 'warning', 5500);
    return fallback;
  };
}
