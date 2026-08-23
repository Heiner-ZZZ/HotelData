import { HttpClient, HttpContext, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { ToastService } from '../../shared/services/toast.service';
import { SUPPRESS_ERROR_TOAST } from './api-context.tokens';
import type { ApiError } from './api-error.model';
import { httpErrorInterceptor } from './http-error.interceptor';

/**
 * The interceptor converts every HttpErrorResponse into a typed `ApiError`
 * with a readable `message`. The backend normally answers `{"detail": "..."}`
 * (a plain string), but some endpoints return a STRUCTURED detail
 * (`{"message", "code", ...}`) so the UI can act on it — e.g. the marketing
 * coupon-conflict error offers «Vincular esta campaña». These tests pin the
 * message extraction for both shapes.
 */
describe('httpErrorInterceptor', () => {
  function setup() {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([httpErrorInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    return {
      http: TestBed.inject(HttpClient),
      httpMock: TestBed.inject(HttpTestingController),
    };
  }

  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('keeps the plain string detail as the ApiError message', () => {
    const { http, httpMock } = setup();
    let error: ApiError | undefined;
    http.get('/api/foo').subscribe({ error: (e: ApiError) => (error = e) });

    httpMock
      .expectOne('/api/foo')
      .flush({ detail: 'Hotel no encontrado.' }, { status: 400, statusText: 'Bad Request' });

    expect(error?.status).toBe(400);
    expect(error?.message).toBe('Hotel no encontrado.');
    expect(error?.details).toEqual({ detail: 'Hotel no encontrado.' });
  });

  it('extracts the message from a structured object detail (code + message)', () => {
    const { http, httpMock } = setup();
    let error: ApiError | undefined;
    http.post('/api/foo', {}).subscribe({ error: (e: ApiError) => (error = e) });

    httpMock.expectOne('/api/foo').flush(
      {
        detail: {
          message: 'El código LUNA15 ya existe en la campaña «Luna de miel» de Tarifas.',
          code: 'COUPON_CODE_EXISTS',
          campaign_id: 'PC-1-luna-de-miel',
          campaign_name: 'Luna de miel',
        },
      },
      { status: 400, statusText: 'Bad Request' },
    );

    expect(error?.status).toBe(400);
    expect(error?.message).toBe('El código LUNA15 ya existe en la campaña «Luna de miel» de Tarifas.');
    expect(error?.details).toEqual({
      detail: {
        message: 'El código LUNA15 ya existe en la campaña «Luna de miel» de Tarifas.',
        code: 'COUPON_CODE_EXISTS',
        campaign_id: 'PC-1-luna-de-miel',
        campaign_name: 'Luna de miel',
      },
    });
  });

  it('falls back to the nested detail string inside an object detail', () => {
    const { http, httpMock } = setup();
    let error: ApiError | undefined;
    http.get('/api/foo').subscribe({ error: (e: ApiError) => (error = e) });

    httpMock
      .expectOne('/api/foo')
      .flush({ detail: { detail: 'Detalle anidado' } }, { status: 422, statusText: 'Unprocessable' });

    expect(error?.message).toBe('Detalle anidado');
  });

  it('lets a top-level body message win over the detail', () => {
    const { http, httpMock } = setup();
    let error: ApiError | undefined;
    http.get('/api/foo').subscribe({ error: (e: ApiError) => (error = e) });

    httpMock
      .expectOne('/api/foo')
      .flush({ message: 'Mensaje de nivel superior' }, { status: 400, statusText: 'Bad Request' });

    expect(error?.message).toBe('Mensaje de nivel superior');
  });

  it('emits a toast for the readable message (global safety net)', () => {
    const { http, httpMock } = setup();
    const toast = TestBed.inject(ToastService);
    const spy = jest.spyOn(toast, 'error');
    let error: ApiError | undefined;
    http.get('/api/foo').subscribe({ error: (e: ApiError) => (error = e) });

    httpMock
      .expectOne('/api/foo')
      .flush({ detail: 'Algo salió mal.' }, { status: 500, statusText: 'Server Error' });

    expect(error?.status).toBe(500);
    expect(spy).toHaveBeenCalledWith('Algo salió mal.');
  });

  it('no emite toast cuando la request marca SUPPRESS_ERROR_TOAST (flujos que ya reportan)', () => {
    const { http, httpMock } = setup();
    const toast = TestBed.inject(ToastService);
    const spy = jest.spyOn(toast, 'error');
    let error: ApiError | undefined;
    http
      .get('/api/foo', { context: new HttpContext().set(SUPPRESS_ERROR_TOAST, true) })
      .subscribe({ error: (e: ApiError) => (error = e) });

    httpMock
      .expectOne('/api/foo')
      .flush({ detail: 'Algo salió mal.' }, { status: 500, statusText: 'Server Error' });

    // El error sigue tipado (ApiError) para el catch del llamador…
    expect(error?.status).toBe(500);
    expect(error?.message).toBe('Algo salió mal.');
    // …pero sin toast duplicado: el flujo (ej. bulk) ya lo reporta resumido.
    expect(spy).not.toHaveBeenCalled();
  });
});
