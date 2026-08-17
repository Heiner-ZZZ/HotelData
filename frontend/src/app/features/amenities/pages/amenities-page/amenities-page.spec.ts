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
import { AmenitiesPageComponent, impliesHighFloor, impliesLateArrival, impliesPetRelated } from './amenities-page';

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
      saveSpecialRequests: jest.fn(),
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

  // ─── Reglas de negocio de peticiones especiales ───
  type RawRequest = {
    label: string;
    unit_price: number;
    chargeable: boolean;
    pet_related: boolean;
    high_floor: boolean;
    late_arrival: boolean;
  };

  function raw(over: Partial<RawRequest> = {}): RawRequest {
    return {
      label: 'Cama extra', unit_price: 15, chargeable: true,
      pet_related: false, high_floor: false, late_arrival: false,
      ...over,
    };
  }

  async function seedRequests(
    ctx: {
      http: HttpTestingController;
      fixture: { detectChanges(): void };
    },
    requests: RawRequest[],
  ) {
    ctx.http.expectOne('/api/management/amenities?prop_id=1&room_type_id=').flush({
      hotel: { prop_id: 1, display_name: 'Hotel Test', country_display_name: '', review_score_label: '' },
      performance: { avg_price_label: '', source_collection: '' },
      amenities: { active_amenities: [], catalog: [] },
      content_page: { description: '' },
      images: [],
      facilities: [],
      room_types: [],
      special_requests: requests,
      high_floor_from: 3,
    });
    await new Promise<void>((resolve) => setTimeout(resolve, 0));
    ctx.fixture.detectChanges();
  }

  it('detecta las reglas implicadas por el nombre de la petición', () => {
    expect(impliesHighFloor('Piso alto')).toBe(true);
    expect(impliesHighFloor('Cama extra')).toBe(false);
    expect(impliesLateArrival('Llegada tarde')).toBe(true);
    expect(impliesLateArrival('Cama extra')).toBe(false);
    expect(impliesPetRelated('Mascotas (Pet friendly)')).toBe(true);
    expect(impliesPetRelated('Cama extra')).toBe(false);
  });

  it('oculta las reglas de negocio por defecto (modo lectura sin sección)', async () => {
    const ctx = setup('especialsPeticions');
    await seedRequests(ctx, [raw()]);

    expect(ctx.fixture.nativeElement.querySelector('.rules-toggle')).toBeNull();
    expect(ctx.fixture.nativeElement.querySelector('.rules-panel')).toBeNull();
  });

  it('en modo edición muestra las reglas colapsadas y las expande al hacer click', async () => {
    const ctx = setup('especialsPeticions');
    await seedRequests(ctx, [raw()]);
    ctx.component.startRequestsEditing();
    ctx.fixture.detectChanges();

    expect(ctx.fixture.nativeElement.querySelector('.rules-toggle')).not.toBeNull();
    expect(ctx.fixture.nativeElement.querySelector('.rules-panel')).toBeNull();

    ctx.component.toggleRulesExpanded('Cama extra');
    ctx.fixture.detectChanges();
    expect(ctx.fixture.nativeElement.querySelector('.rules-panel')).not.toBeNull();
  });

  it('no renderiza toggle circular para peticiones cuyo nombre ya implica la regla', async () => {
    const ctx = setup('especialsPeticions');
    await seedRequests(ctx, [
      raw({ label: 'Piso alto', unit_price: 0, chargeable: false, high_floor: true }),
      raw({ label: 'Llegada tarde', unit_price: 0, chargeable: false, late_arrival: true }),
      raw({ label: 'Mascotas (Pet friendly)', unit_price: 20, pet_related: true }),
      raw(),
    ]);
    ctx.component.startRequestsEditing();
    ctx.fixture.detectChanges();

    const rows = [...ctx.fixture.nativeElement.querySelectorAll('.request-row')] as HTMLElement[];
    const checkboxesOf = (label: string) => {
      const row = rows.find((r) => r.querySelector('.request-row-label')?.textContent?.trim() === label)!;
      ctx.component.toggleRulesExpanded(label);
      ctx.fixture.detectChanges();
      return row.querySelectorAll('.rules-panel input[type="checkbox"]').length;
    };

    expect(checkboxesOf('Piso alto')).toBe(2); // mascotas + llegada tarde (sin piso alto)
    expect(checkboxesOf('Llegada tarde')).toBe(2); // mascotas + piso alto (sin llegada tarde)
    expect(checkboxesOf('Mascotas (Pet friendly)')).toBe(2); // piso alto + llegada tarde (sin mascotas)
    expect(checkboxesOf('Cama extra')).toBe(3); // las tres reglas aplican
  });

  it('envía al guardar los flags implícitos por el nombre de la petición', async () => {
    const ctx = setup('especialsPeticions');
    await seedRequests(ctx, [
      raw({ label: 'Piso alto', unit_price: 0, chargeable: false, high_floor: false }),
      raw({ label: 'Llegada tarde', unit_price: 0, chargeable: false, late_arrival: false }),
      raw(),
    ]);
    const pending = new Subject<{
      special_requests: RawRequest[];
      high_floor_from: number;
    }>();
    (ctx.api as unknown as { saveSpecialRequests: jest.Mock }).saveSpecialRequests.mockReturnValue(pending);

    ctx.component.saveRequests();

    const payload = (ctx.api as unknown as { saveSpecialRequests: jest.Mock }).saveSpecialRequests.mock.calls[0][0];
    const flagsByLabel = Object.fromEntries(
      (payload.special_requests as { label: string; flags: string[] }[]).map((r) => [r.label, r.flags]),
    );
    expect(flagsByLabel['Piso alto']).toContain('high_floor');
    expect(flagsByLabel['Llegada tarde']).toContain('late_arrival');
    expect(flagsByLabel['Cama extra']).not.toContain('high_floor');
    pending.complete();
  });
});
