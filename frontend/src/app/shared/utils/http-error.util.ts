import { HttpErrorResponse } from '@angular/common/http';

/**
 * Extrae el status HTTP de un error sin importar su forma concreta.
 *
 * El interceptor global `httpErrorInterceptor` convierte cada
 * `HttpErrorResponse` en un `ApiError` plano (`{ status, message, details }`),
 * por lo que `err instanceof HttpErrorResponse` es FALSE en la app en vivo
 * (solo es cierto en tests con `HttpTestingController`, que entrega el error
 * crudo). Este helper cubre ambas formas y evita que los checks de status
 * (403/404/401) fallen silenciosamente y degraden al estado 'error' genérico.
 */
export function getErrorStatus(err: unknown): number | undefined {
  if (err instanceof HttpErrorResponse) return err.status;
  if (err && typeof err === 'object' && 'status' in err) {
    const status = (err as { status?: unknown }).status;
    return typeof status === 'number' ? status : undefined;
  }
  return undefined;
}

/**
 * Extrae un mensaje legible de un error sin importar su forma concreta.
 *
 * Cubre: `HttpErrorResponse` (body `{ detail }` o `message`), el `ApiError`
 * plano del interceptor (cuyo `message` ya es el detail del server y cuyo
 * `details` conserva el body original), `Error` y strings. Devuelve
 * `undefined` cuando no hay mensaje útil.
 */
export function getErrorMessage(err: unknown): string | undefined {
  if (err instanceof HttpErrorResponse) {
    const body = err.error as { detail?: unknown } | null;
    if (body && typeof body.detail === 'string' && body.detail.trim()) return body.detail;
    if (err.message) return err.message;
    return undefined;
  }
  if (err && typeof err === 'object') {
    const anyErr = err as { message?: unknown; details?: unknown; error?: unknown };
    if (typeof anyErr.message === 'string' && anyErr.message.trim()) return anyErr.message;
    const details = anyErr.details as { detail?: unknown } | null;
    if (details && typeof details.detail === 'string' && details.detail.trim()) return details.detail;
    if (err instanceof Error) return err.message;
  }
  return undefined;
}
