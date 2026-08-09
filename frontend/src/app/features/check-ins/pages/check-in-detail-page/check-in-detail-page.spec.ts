import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { of } from 'rxjs';

import { httpErrorInterceptor } from '../../../../core/api/http-error.interceptor';
import { ToastService } from '../../../../shared/services/toast.service';
import { CheckInDetailPageComponent } from './check-in-detail-page';

describe('CheckInDetailPageComponent', () => {
  async function render403() {
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

    await TestBed.configureTestingModule({
      imports: [CheckInDetailPageComponent],
      providers: [
        // Incluir el interceptor real para probar el camino vivo: el 403 llega
        // como ApiError plano ({ status, message }), no como HttpErrorResponse.
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

    const fixture = TestBed.createComponent(CheckInDetailPageComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();

    const httpTesting = TestBed.inject(HttpTestingController);
    const req = httpTesting.expectOne((r) => r.url.includes('/management/check-ins/BK-1/detail'));
    req.flush({ detail: 'Permiso requerido: check-ins.read' }, { status: 403, statusText: 'Forbidden' });

    // httpResource asienta el error en un microtask (promise interna); esperar
    // a que el estado 'forbidden' y los efectos se asienten antes de leer.
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
    expect(() => component.totalPrice()).not.toThrow();
    expect(() => component.assignedRoomsStatuses()).not.toThrow();
    expect(() => component.totalNights()).not.toThrow();
    expect(consoleSpy).not.toHaveBeenCalled();
  });
});
