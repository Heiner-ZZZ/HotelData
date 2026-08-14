import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, Router } from '@angular/router';
import { of, Subject } from 'rxjs';

import { ToastService } from '../../../../shared/services/toast.service';
import { GeoCatalogApiService } from '../../services/geo-catalog-api.service';
import { GeoCatalogPageComponent } from './geo-catalog-page';

describe('GeoCatalogPageComponent', () => {
  function setup(initialParams: Record<string, string> = {}) {
    const paramMap = convertToParamMap(initialParams);
    const router = {
      navigate: jest.fn(),
      events: new Subject<unknown>().asObservable(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as never;

    TestBed.configureTestingModule({
      imports: [GeoCatalogPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: paramMap }, queryParamMap: of(paramMap) },
        },
        { provide: Router, useValue: router },
        { provide: GeoCatalogApiService, useValue: {} },
        { provide: ToastService, useValue: { success: jest.fn(), error: jest.fn() } },
      ],
    });

    const fixture = TestBed.createComponent(GeoCatalogPageComponent);
    fixture.detectChanges();
    return {
      fixture,
      component: fixture.componentInstance,
      http: TestBed.inject(HttpTestingController),
    };
  }

  const flush = () => new Promise<void>((resolve) => setTimeout(resolve, 0));

  it('solicita visitor countries al endpoint real /api/geo/visitor-countries', () => {
    const { http } = setup();
    http.expectOne('/api/geo/visitor-countries').flush({ items: [] });
  });

  it('solicita visitor destinations al endpoint real /api/geo/visitor-destinations', () => {
    const { http } = setup({ type: 'visitor-destination' });
    http.expectOne('/api/geo/visitor-destinations').flush({ items: [] });
  });

  it('solicita visitor sites al endpoint real /api/geo/visitor-sites', () => {
    const { http } = setup({ type: 'visitor-site' });
    http.expectOne('/api/geo/visitor-sites').flush({ items: [] });
  });

  it('solicita visitor hotels al endpoint real /api/geo/visitor-hotels', () => {
    const { http } = setup({ type: 'visitor-hotel' });
    http.expectOne('/api/geo/visitor-hotels').flush({ items: [] });
  });

  it('solicita el catálogo genérico al endpoint real /api/geo/entries', () => {
    const { http } = setup({ type: 'country' });
    http.expectOne('/api/geo/entries?type=country').flush({ items: [], total: 0, page: 1, page_size: 50, total_pages: 1, has_next: false, has_prev: false });
  });

  it('mapea los items de visitor countries a GeoEntry y los renderiza', async () => {
    const { fixture, http } = setup();
    http
      .expectOne('/api/geo/visitor-countries')
      .flush({ items: [{ visitor_location_country_id: 187, country_display_name: 'Ecuador' }] });
    await flush();
    fixture.detectChanges();

    expect(fixture.componentInstance.data()?.items[0]).toMatchObject({ id: '187', code: '187', name: 'Ecuador' });
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Ecuador');
  });

  it('mapea los items enriquecidos del catálogo genérico (id/code/name)', async () => {
    const { fixture, http } = setup({ type: 'country' });
    http.expectOne('/api/geo/entries?type=country').flush({
      items: [
        {
          id: '64f1a2b3c4d5e6f7a8b9c0d1',
          type: 'country',
          code: 'EC',
          name: 'Ecuador',
          countryCode: '',
          stateCode: '',
          category: '',
          isoCode: 'EC',
          latitude: null,
          longitude: null,
          isActive: true,
          createdAt: '',
          updatedAt: null,
        },
      ],
      total: 1,
      page: 1,
      page_size: 50,
      total_pages: 1,
      has_next: false,
      has_prev: false,
    });
    await flush();
    fixture.detectChanges();

    expect(fixture.componentInstance.data()?.items[0]).toMatchObject({ id: '64f1a2b3c4d5e6f7a8b9c0d1', code: 'EC', name: 'Ecuador' });
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Ecuador');
  });
});
