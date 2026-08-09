import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap } from '@angular/router';
import { of, Subject } from 'rxjs';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ToastService } from '../../../../shared/services/toast.service';
import { ConfirmDialogService } from '../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { AmenitiesApiService } from '../../services/amenities-api.service';
import { AmenitiesPageComponent } from './amenities-page';

describe('AmenitiesPageComponent', () => {
  function setup() {
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

    TestBed.configureTestingModule({
      imports: [AmenitiesPageComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: ActivatedRoute,
          useValue: { queryParamMap: of(convertToParamMap({ prop_id: '1' })) },
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
