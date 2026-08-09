import { HttpErrorResponse } from '@angular/common/http';

import { getErrorStatus, getErrorMessage } from './http-error.util';

describe('getErrorStatus', () => {
  it('lee el status de un HttpErrorResponse (camino de tests sin interceptor)', () => {
    const err = new HttpErrorResponse({ status: 403, statusText: 'Forbidden' });
    expect(getErrorStatus(err)).toBe(403);
  });

  it('lee el status de un ApiError plano del interceptor (camino vivo)', () => {
    expect(getErrorStatus({ status: 403, message: 'Permiso requerido: check-ins.read' })).toBe(403);
  });

  it('devuelve undefined para errores sin status', () => {
    expect(getErrorStatus(new Error('boom'))).toBeUndefined();
    expect(getErrorStatus({ status: '403' })).toBeUndefined();
    expect(getErrorStatus(null)).toBeUndefined();
    expect(getErrorStatus(undefined)).toBeUndefined();
  });
});

describe('getErrorMessage', () => {
  it('extrae el detail del body de un HttpErrorResponse', () => {
    const err = new HttpErrorResponse({ status: 400, error: { detail: 'Correo ya registrado' } });
    expect(getErrorMessage(err)).toBe('Correo ya registrado');
  });

  it('extrae el message del ApiError del interceptor (camino vivo)', () => {
    expect(getErrorMessage({ status: 400, message: 'Correo ya registrado' })).toBe('Correo ya registrado');
  });

  it('cae al detail conservado en details del ApiError si no hay message', () => {
    expect(getErrorMessage({ status: 400, message: '', details: { detail: 'Detalle del server' } }))
      .toBe('Detalle del server');
  });

  it('devuelve undefined para errores sin mensaje útil', () => {
    expect(getErrorMessage(null)).toBeUndefined();
    expect(getErrorMessage(undefined)).toBeUndefined();
    expect(getErrorMessage({ status: 500 })).toBeUndefined();
  });
});
