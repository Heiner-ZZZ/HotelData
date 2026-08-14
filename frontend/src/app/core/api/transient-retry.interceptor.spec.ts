import { HttpClient } from '@angular/common/http';
import { HttpErrorResponse, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { fakeAsync, flushMicrotasks, TestBed, tick } from '@angular/core/testing';

import { transientRetryInterceptor } from './transient-retry.interceptor';

/**
 * The stack proxies /api through nginx to a uvicorn server running with
 * `--reload`. Every backend restart (docker compose up, a saved server file)
 * leaves a ~1-3s window where nginx answers 502. These tests pin the retry
 * behavior that lets idempotent GETs self-heal across that window.
 */
describe('transientRetryInterceptor', () => {
  function setup() {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([transientRetryInterceptor])),
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

  it('retries a GET that fails with 502 and succeeds on the second attempt', fakeAsync(() => {
    const { http, httpMock } = setup();
    let result: unknown;
    http.get('/api/foo').subscribe((r) => (result = r));

    const first = httpMock.expectOne('/api/foo');
    first.flush({}, { status: 502, statusText: 'Bad Gateway' });
    flushMicrotasks();

    // Backoff delay must elapse before the retry is fired.
    expect(() => httpMock.expectOne('/api/foo')).toThrow();

    tick(500);
    flushMicrotasks();
    const second = httpMock.expectOne('/api/foo');
    second.flush({ ok: true });
    flushMicrotasks();

    expect(result).toEqual({ ok: true });
  }));

  it('gives up after the max attempts and rethrows the gateway error', fakeAsync(() => {
    const { http, httpMock } = setup();
    let error: unknown;
    http.get('/api/foo').subscribe({ error: (e) => (error = e) });

    httpMock.expectOne('/api/foo').flush({}, { status: 503, statusText: 'Service Unavailable' });
    flushMicrotasks();
    tick(500);
    flushMicrotasks();

    httpMock.expectOne('/api/foo').flush({}, { status: 503, statusText: 'Service Unavailable' });
    flushMicrotasks();
    tick(1500);
    flushMicrotasks();

    httpMock.expectOne('/api/foo').flush({}, { status: 503, statusText: 'Service Unavailable' });
    flushMicrotasks();

    expect(error).toBeInstanceOf(HttpErrorResponse);
    expect((error as HttpErrorResponse).status).toBe(503);
  }));

  it('retries 504 the same way (gateway timeout)', fakeAsync(() => {
    const { http, httpMock } = setup();
    let result: unknown;
    http.get('/api/foo').subscribe((r) => (result = r));

    httpMock.expectOne('/api/foo').flush({}, { status: 504, statusText: 'Gateway Timeout' });
    flushMicrotasks();
    tick(500);
    flushMicrotasks();

    httpMock.expectOne('/api/foo').flush({ ok: true });
    flushMicrotasks();

    expect(result).toEqual({ ok: true });
  }));

  it('does NOT retry non-GET methods (POST)', fakeAsync(() => {
    const { http, httpMock } = setup();
    let error: unknown;
    http.post('/api/foo', {}).subscribe({ error: (e) => (error = e) });

    httpMock.expectOne('/api/foo').flush({}, { status: 502, statusText: 'Bad Gateway' });
    flushMicrotasks();
    tick(5000);
    flushMicrotasks();

    expect(() => httpMock.expectOne('/api/foo')).toThrow();
    expect(error).toBeInstanceOf(HttpErrorResponse);
    expect((error as HttpErrorResponse).status).toBe(502);
  }));

  it('does NOT retry non-transient statuses (404)', fakeAsync(() => {
    const { http, httpMock } = setup();
    let error: unknown;
    http.get('/api/foo').subscribe({ error: (e) => (error = e) });

    httpMock.expectOne('/api/foo').flush({}, { status: 404, statusText: 'Not Found' });
    flushMicrotasks();
    tick(5000);
    flushMicrotasks();

    expect(() => httpMock.expectOne('/api/foo')).toThrow();
    expect(error).toBeInstanceOf(HttpErrorResponse);
    expect((error as HttpErrorResponse).status).toBe(404);
  }));
});
