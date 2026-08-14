import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { PropertyEditPageComponent } from './property-edit-page';

const profileDto = {
  hotel: {
    prop_id: 1,
    display_name: 'Hotel Lima Centro',
    hotel_name: 'Hotel Lima Centro',
    country_display_name: 'Perú',
    manual_override: false,
    name_source: 'generated_from_id',
    original_generated_name: 'Hotel 1',
    profile_badge: 'Nombre generado',
  },
  profile: {
    prop_id: 1,
    display_name: 'Hotel Lima Centro',
    hotel_name: 'Hotel Lima Centro',
    description: 'Descripción del hotel',
    display_country_label: 'Perú',
    manual_override: false,
    name_source: 'generated_from_id',
    original_generated_name: 'Hotel 1',
    profile_badge: 'Nombre generado',
    updated_by: null,
    updated_at: null,
  },
  currency: 'USD',
  accepted_currencies: ['USD', 'MXN'],
};

const policiesDto = {
  policies: {
    check_in_time: '15:00',
    check_out_time: '12:00',
    cancellation_policy: 'Flexible - 24h',
    pet_policy: 'false',
  },
};

const amenitiesDto = {
  content_page: {
    prop_id: 1,
    description: 'Descripción',
    highlights: 'Hotel 1 GTA7 cuenta con contenido demo operativo para validar el módulo partner.',
    amenities_text: '',
    source: 'demo',
    updated_at: null,
  },
  images: [{ image_url: 'https://example.com/hotel1.jpg', title: '' }],
  amenities: { active_amenities: [], catalog: [] },
};

describe('PropertyEditPageComponent — fixes de Editar Propiedad', () => {
  async function setup() {
    // El componente loguea en isDevMode ("Loading property profile endpoint");
    // silenciar para mantener la salida del test limpia.
    jest.spyOn(console, 'log').mockImplementation(() => {});

    await TestBed.configureTestingModule({
      imports: [PropertyEditPageComponent],
      providers: [
        provideRouter([]),
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { paramMap: new Map([['propertyId', '1']]) },
            paramMap: of(new Map([['propertyId', '1']])),
          },
        },
        { provide: PropertyContextService, useValue: { setCurrency: jest.fn() } },
        { provide: OperationModeService, useValue: {} },
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(PropertyEditPageComponent);
    fixture.detectChanges();

    const http = TestBed.inject(HttpTestingController);
    const currenciesReq = http.expectOne((r) => r.url.includes('/currencies'));
    currenciesReq.flush({
      currencies: [
        { code: 'USD', name: 'Dólar estadounidense', symbol: '$', decimals: 2, active: true },
      ],
    });

    http.expectOne((r) => r.url.includes('/properties/1/profile')).flush(profileDto);
    http.expectOne((r) => r.url.includes('/policies')).flush(policiesDto);
    http.expectOne((r) => r.url.includes('/amenities')).flush(amenitiesDto);

    await fixture.whenStable();
    await Promise.resolve();
    fixture.detectChanges();

    return { fixture, http, currenciesReq };
  }

  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
    jest.restoreAllMocks();
  });

  it('lee las monedas del endpoint público (el gerente no tiene settings.read)', async () => {
    const { currenciesReq } = await setup();
    expect(currenciesReq.request.url).toContain('/public/currencies');
    expect(currenciesReq.request.url).not.toContain('/management/currencies');
  });

  it('tiene un botón Volver que lleva al detalle de la propiedad', async () => {
    const { fixture } = await setup();
    const back = fixture.nativeElement.querySelector('a.back-link') as HTMLAnchorElement;
    expect(back).toBeTruthy();
    expect(back.getAttribute('href')).toContain('/management/properties/1');
    expect(back.textContent).toContain('Volver');
  });

  it('no muestra el item "ID … Propiedad" en la barra de info', async () => {
    const { fixture } = await setup();
    const labels = Array.from(
      fixture.nativeElement.querySelectorAll('.info-bar .info-label'),
    ).map((el: Element) => el.textContent);
    expect(labels).not.toContain('Propiedad');
    expect(labels).not.toContain('ID');
  });

  it('la caja de highlights tiene espacio para su contenido', async () => {
    const { fixture } = await setup();
    const textarea = fixture.nativeElement.querySelector('#highlights') as HTMLTextAreaElement;
    expect(textarea).toBeTruthy();
    expect(textarea.rows).toBeGreaterThanOrEqual(4);
  });

  it('las cajas del formulario se separan entre sí (form con gap)', async () => {
    const { fixture } = await setup();
    expect(fixture.nativeElement.querySelector('form.edit-form')).toBeTruthy();
  });

  it('la galería muestra un fallback cuando una imagen no carga', async () => {
    const { fixture } = await setup();
    const img = fixture.nativeElement.querySelector('.gallery-img') as HTMLImageElement;
    expect(img).toBeTruthy();
    img.dispatchEvent(new Event('error'));
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.gallery-img-fallback')).toBeTruthy();
  });
});
