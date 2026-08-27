import { readFileSync } from 'node:fs';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

const sass = (tryRequire('sass') ?? tryRequire('sass-embedded')) as { compileString: (s: string) => { css: string } };
function tryRequire(name: string): unknown {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  try { return require(name); } catch { return null; }
}

import { OnboardingPropertyComponent } from './onboarding-property';

/** Este preset de Jest no inyecta los estilos del componente en el DOM:
 *  el contrato visual se verifica compilando el SCSS real del componente. */
function compiledCss(): string {
  const scss = readFileSync(`${__dirname}/onboarding-property.scss`, 'utf-8');
  return sass.compileString(scss).css.replace(/\s+/g, '');
}

/* El picker hijo inicializa MapLibre, que requiere WebGL (ausente en jsdom):
   se stubbea el engine externo para montar la página completa. */
jest.mock('maplibre-gl', () => {
  class StubMarker {
    setLngLat = () => this;
    addTo = () => this;
    on = () => this;
    remove = () => this;
  }
  return {
    __esModule: true,
    default: {
      Map: class {
        addControl = () => undefined;
        on = () => undefined;
        easeTo = () => undefined;
        remove = () => undefined;
        loaded = () => true;
      },
      Marker: StubMarker,
      NavigationControl: class {},
      AttributionControl: class {},
    },
  };
});

const PRICING_PLANS = {
  plans: [
    { band: 1, label: 'B1', min_rooms: 1, max_rooms: 10, monthly_usd: 39, annual_monthly_usd: 32 },
    { band: 3, label: 'B3', min_rooms: 26, max_rooms: 60, monthly_usd: 99, annual_monthly_usd: 82 },
    { band: 5, label: 'B5', min_rooms: 101, max_rooms: 300, monthly_usd: 199, annual_monthly_usd: 165 },
  ],
};

describe('OnboardingPropertyComponent — tarjetas "Tamaño de tu alojamiento"', () => {
  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  async function setup() {
    TestBed.configureTestingModule({
      imports: [OnboardingPropertyComponent],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    const fixture = TestBed.createComponent(OnboardingPropertyComponent);
    fixture.detectChanges();

    const http = TestBed.inject(HttpTestingController);
    // httpResource dispara los GET en un scheduler diferido: se hace polling
    // con match() hasta consumir los cuatro catálogos públicos.
    const routes = [
      { urlPart: '/public/currencies', body: { currencies: [] } },
      { urlPart: '/public/countries', body: { countries: [] } },
      { urlPart: '/public/pricing-plans', body: PRICING_PLANS },
      { urlPart: 'doc_type=terms_hotel_partner', body: { version: 1 } },
    ];
    for (let tick = 0; tick < 50; tick++) {
      const tb = TestBed as unknown as { tick?: () => void; flushEffects?: () => void };
      (tb.tick ?? tb.flushEffects)?.call(tb);
      await Promise.resolve();
      for (const route of routes) {
        for (const req of http.match((r) => r.url.includes(route.urlPart))) {
          req.flush(route.body);
        }
      }
      if (http.match(() => true).length === 0) break;
      await new Promise((resolve) => setTimeout(resolve, 10));
    }

    await fixture.whenStable();
    fixture.detectChanges();
    return fixture;
  }

  it('las tarjetas de plan tienen esquinas superiores rectas (sin bordes curvos top)', async () => {
    const fixture = await setup();
    const el = fixture.nativeElement as HTMLElement;
    const bodies = el.querySelectorAll<HTMLElement>('.plan-option__body');
    expect(bodies.length).toBe(3);

    // Contrato visual sobre el SCSS compilado (jsdom no aplica estilos).
    const bodyRule = compiledCss().match(/\.plan-option__body{([^}]*)}/);
    expect(bodyRule).not.toBeNull();
    const declarations = bodyRule![1];
    expect(declarations).toMatch(/border-radius:0(?![^;]*%)/);
  });

  it('solo ofrece tipos de propiedad que operan como un hotel (sin apartamento ni cabaña)', async () => {
    const fixture = await setup();
    const comp = fixture.componentInstance as OnboardingPropertyComponent;

    // Contrato de catálogo: el componente expone la lista filtrada.
    // (El valor DOM de los radios con formControlName no es confiable en
    // jsdom — el binding [value] se pierde en la serialización; el contrato
    // real es la lista expuesta + los chips renderizados.)
    expect(comp.propertyTypes.map((t) => t.value)).toEqual([
      'hotel',
      'hostal',
      'bed_breakfast',
      'resort',
      'boutique',
    ]);

    // El template renderiza un chip por tipo (misma lista).
    const chips = fixture.nativeElement.querySelectorAll<HTMLElement>('.type-chip');
    expect(chips.length).toBe(5);

    const labels = Array.from(
      fixture.nativeElement.querySelectorAll<HTMLElement>('.type-chip__body span:last-child'),
    );
    expect(labels.map((l) => l.textContent?.trim())).toEqual([
      'Hotel',
      'Hostal',
      'Bed & Breakfast',
      'Resort',
      'Boutique',
    ]);
  });

  it('ordena los datos del hotel antes del mapa, con línea divisoria verde entre columnas', async () => {
    const fixture = await setup();
    const grid = fixture.nativeElement.querySelector('.form-grid') as HTMLElement;
    const children = Array.from(grid.children) as HTMLElement[];

    const indexOf = (fn: (n: HTMLElement) => boolean) => children.findIndex(fn);
    const phone = indexOf((n) => !!n.querySelector('[formcontrolname="contact_phone"]'));
    const currency = indexOf((n) => !!n.querySelector('[formcontrolname="currency"]'));
    const rooms = indexOf((n) => !!n.querySelector('[formcontrolname="total_rooms"]'));
    const desc = indexOf((n) => !!n.querySelector('[formcontrolname="description"]'));
    const map = indexOf((n) => n.classList.contains('location-picker-field'));
    const divider = indexOf((n) => n.classList.contains('section-divider'));

    // Los 4 campos del hotel existen y van ANTES del mapa.
    expect(phone).toBeGreaterThan(-1);
    expect(currency).toBeGreaterThan(-1);
    expect(rooms).toBeGreaterThan(-1);
    expect(desc).toBeGreaterThan(-1);
    expect(map).toBeGreaterThan(-1);
    expect(Math.max(phone, currency, rooms, desc)).toBeLessThan(map);

    // La línea separa los datos del cliente (confirm/address) de los del hotel.
    expect(divider).toBeGreaterThan(-1);
    expect(divider).toBeLessThan(phone);

    // El mapa es el último elemento del grid (a lo largo de las dos columnas).
    expect(map).toBe(children.length - 1);

    // La línea es verde oscuro intenso (--success-strong), no hardcodeada.
    const dividerRule = compiledCss().match(/\.section-divider\{([^}]*)\}/);
    expect(dividerRule).not.toBeNull();
    expect(dividerRule![1]).toContain('var(--success-strong)');
  });
});
