import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { BehaviorSubject, of, Subject } from 'rxjs';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { AmenitiesApiService } from '../../services/amenities-api.service';
import { AMENITIES_ROUTES } from '../../amenities.routes';
import { AmenitiesPageComponent } from './amenities-page';

describe('AmenitiesPageComponent', () => {
  function setup(initialPath = 'servicios') {
    const sectionParamMap$ = new BehaviorSubject(convertToParamMap({ section: initialPath }));
    const router = {
      events: new Subject<unknown>().asObservable(),
      navigate: jest.fn(),
      routerState: { snapshot: { root: { data: {}, firstChild: null } } },
    } as unknown as Router;
    const propertyContext = {
      ready: signal(false),
      singleHotelMode: signal(false),
      currentPropId: signal(1),
      currentCurrency: signal('USD'),
      setProperty: jest.fn(),
      clear: jest.fn(),
    } as unknown as PropertyContextService;
    const api = {
      saveAmenities: jest.fn(),
    } as unknown as AmenitiesApiService;
    const confirmDialog = { open: jest.fn(() => Promise.resolve(true)) } as unknown as ConfirmDialogService;

    const route = {
      queryParamMap: of(convertToParamMap({ prop_id: '1' })),
      paramMap: sectionParamMap$.asObservable(),
      snapshot: {
        url: [{ path: initialPath }],
        paramMap: convertToParamMap({ section: initialPath }),
        queryParamMap: convertToParamMap({ prop_id: '1' }),
      },
    };

    TestBed.configureTestingModule({
      imports: [AmenitiesPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: route,
        },
        { provide: PropertyContextService, useValue: propertyContext },
        { provide: AmenitiesApiService, useValue: api },
        { provide: ConfirmDialogService, useValue: confirmDialog },
      ],
    });

    const fixture = TestBed.createComponent(AmenitiesPageComponent);
    fixture.detectChanges();
    return {
      fixture,
      component: fixture.componentInstance,
      toast: TestBed.inject(ToastService),
      http: TestBed.inject(HttpTestingController),
      api,
      router,
      route,
      sectionParamMap$,
    };
  }

  /** Resolve the amenities httpResource so saveAmenities() has a current viewModel. */
  async function seedAmenities(ctx: {
    http: HttpTestingController;
    fixture: { detectChanges(): void };
  }) {
    ctx.http.expectOne('/api/management/amenities?prop_id=1&room_type_id=').flush({
      hotel: { prop_id: 1, display_name: 'Hotel Test', country_display_name: '', review_score_label: '' },
      performance: { avg_price_label: '', source_collection: '' },
      amenities: { active_amenities: [], catalog: [] },
      content_page: { description: '' },
      images: [],
      facilities: [],
      room_types: [],
    });
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();
  }

  it('inicia en Peticiones especiales cuando la URL usa la ruta especial', async () => {
    const ctx = setup('especialsPeticions');
    await seedAmenities(ctx);

    expect(ctx.component.activeTab()).toBe('requests');
  });

  it('cambia la ruta del navegador al cambiar entre Servicios y Peticiones especiales', async () => {
    const ctx = setup('servicios');
    await seedAmenities(ctx);

    ctx.component.setActiveTab('requests');
    expect(ctx.router.navigate).toHaveBeenCalledWith(
      ['/management/amenities', 'especialsPeticions'],
      { queryParamsHandling: 'merge', replaceUrl: true },
    );
    ctx.sectionParamMap$.next(convertToParamMap({ section: 'especialsPeticions' }));
    expect(ctx.component.activeTab()).toBe('requests');

    ctx.component.setActiveTab('amenities');
    expect(ctx.router.navigate).toHaveBeenCalledWith(
      ['/management/amenities', 'servicios'],
      { queryParamsHandling: 'merge', replaceUrl: true },
    );
    ctx.sectionParamMap$.next(convertToParamMap({ section: 'servicios' }));
    expect(ctx.component.activeTab()).toBe('amenities');
  });

  it('usa una única ruta parametrizada para no recrear el selector al cambiar de sección', () => {
    expect(AMENITIES_ROUTES.map((route) => route.path)).toEqual(['', ':section']);
    expect(AMENITIES_ROUTES[0]).toEqual(expect.objectContaining({
      path: '',
      pathMatch: 'full',
      redirectTo: 'servicios',
    }));
  });

  it('actualiza la pestaña cuando cambia la sección de la URL sin recrear el componente', async () => {
    const ctx = setup('servicios');
    await seedAmenities(ctx);
    const resource = ctx.component.amenitiesResource;

    ctx.sectionParamMap$.next(convertToParamMap({ section: 'especialsPeticions' }));

    expect(ctx.component.activeTab()).toBe('requests');
    expect(ctx.component.amenitiesResource).toBe(resource);
  });

  it('no renderiza banners .notification locales (migrado al toast global)', async () => {
    const ctx = setup();
    await seedAmenities(ctx);

    expect(ctx.fixture.nativeElement.querySelector('.notification')).toBeNull();
  });

  it('muestra el toast global al guardar los servicios (sin banner local)', async () => {
    const ctx = setup();
    await seedAmenities(ctx);
    const pending = new Subject<{ activeAmenities: string[] }>();
    (ctx.api as unknown as { saveAmenities: jest.Mock }).saveAmenities.mockReturnValue(pending);

    ctx.component.saveAmenities();
    pending.next({ activeAmenities: ['Wi-Fi'] });
    pending.complete();

    expect(ctx.toast.toasts().some((t) => t.message === 'Servicios actualizados' && t.type === 'success')).toBe(true);
  });

  it('muestra el error del backend en el toast global al fallar el guardado', async () => {
    const ctx = setup();
    await seedAmenities(ctx);
    const pending = new Subject<{ activeAmenities: string[] }>();
    (ctx.api as unknown as { saveAmenities: jest.Mock }).saveAmenities.mockReturnValue(pending);

    ctx.component.saveAmenities();
    pending.error({ message: 'Error de prueba' });

    expect(ctx.toast.toasts().some((t) => t.message === 'Error de prueba' && t.type === 'error')).toBe(true);
  });
});
