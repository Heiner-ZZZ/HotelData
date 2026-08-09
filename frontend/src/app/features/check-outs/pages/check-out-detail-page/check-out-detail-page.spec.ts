import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';

import { httpErrorInterceptor } from '../../../../core/api/http-error.interceptor';
import { ToastService } from '../../../../shared/services/toast.service';
import { CheckOutDetailPageComponent } from './check-out-detail-page';

describe('CheckOutDetailPageComponent', () => {
  async function render403() {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    await TestBed.configureTestingModule({
      imports: [CheckOutDetailPageComponent],
      providers: [
        // Interceptor real → el 403 llega como ApiError plano (camino vivo),
        // no como HttpErrorResponse.
        provideHttpClient(withInterceptors([httpErrorInterceptor])),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { paramMap: { get: () => 'BK-1' } },
            paramMap: of(new Map([['bookingId', 'BK-1']])),
          },
        },
        { provide: Router, useValue: { events: of() } },
        { provide: ToastService, useValue: { error: jest.fn() } },
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(CheckOutDetailPageComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();

    const httpTesting = TestBed.inject(HttpTestingController);
    const req = httpTesting.expectOne((r) => r.url.includes('/management/check-outs/BK-1/detail'));
    req.flush({ detail: 'Permiso requerido: check-outs.read' }, { status: 403, statusText: 'Forbidden' });

    await fixture.whenStable();
    await Promise.resolve();
    await Promise.resolve();
    fixture.detectChanges();

    return { fixture, component, consoleSpy, httpTesting };
  }

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('data() devuelve null sin lanzar cuando el detalle responde 403', async () => {
    const { component } = await render403();
    expect(() => component.data()).not.toThrow();
    expect(component.data()).toBeNull();
  });

  it('viewState pasa a forbidden en 403 y la página muestra el aviso de permiso', async () => {
    const { fixture, component } = await render403();
    expect(component.viewState()).toBe('forbidden');
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('permiso');
  });

  it('no spamea la consola tras el 403 y los computeds derivados no lanzan', async () => {
    const { component, consoleSpy } = await render403();
    expect(() => component.roomTotal()).not.toThrow();
    expect(() => component.chargesTotal()).not.toThrow();
    expect(() => component.grandTotal()).not.toThrow();
    expect(consoleSpy).not.toHaveBeenCalled();
  });
});
