import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { WelcomePageComponent } from './welcome-page';

// jsdom no implementa matchMedia; ThemeService resuelve 'system' con él.
if (!window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }),
  });
}

describe('WelcomePageComponent — accesibilidad (Chrome Issues)', () => {
  function setup() {
    TestBed.configureTestingModule({
      imports: [WelcomePageComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    const fixture = TestBed.createComponent(WelcomePageComponent);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();

    // Los httpResource del constructor disparan dos GETs; los vaciamos.
    http
      .expectOne((r) => r.url.includes('/hotels/availability'))
      .flush({ items: [] });
    http
      .expectOne((r) => r.url.includes('/public/currencies'))
      .flush({ currencies: [] });
    fixture.detectChanges();

    return { fixture, http };
  }

  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('el select de moneda lleva id y name (evita el aviso de Issues)', () => {
    const { fixture } = setup();
    const select = fixture.nativeElement.querySelector('select.chip__select') as HTMLSelectElement;
    expect(select).toBeTruthy();
    expect(select.id).toBe('welcome-currency');
    expect(select.name).toBe('currency');
  });
});

describe('WelcomePageComponent — siempre modo claro', () => {
  afterEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-theme');
  });

  it('fuerza modo claro aun con preferencia oscura y lo libera al salir de la ruta', () => {
    // Preferencia guardada: oscuro. El /welcome debe verse claro igual.
    localStorage.setItem('hoteldata-theme-preference', 'dark');
    localStorage.setItem('hoteldata-theme', 'dark');

    TestBed.configureTestingModule({
      imports: [WelcomePageComponent],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    const fixture = TestBed.createComponent(WelcomePageComponent);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http
      .expectOne((r) => r.url.includes('/hotels/availability'))
      .flush({ items: [] });
    http
      .expectOne((r) => r.url.includes('/public/currencies'))
      .flush({ currencies: [] });
    fixture.detectChanges();

    // Montado: claro, pese a la preferencia oscura.
    expect(document.documentElement.getAttribute('data-theme')).toBe('light');

    // Al salir de la ruta, la preferencia del usuario vuelve a mandar.
    fixture.destroy();
    expect(document.documentElement.getAttribute('data-theme')).toBe('dark');
    TestBed.inject(HttpTestingController).verify();
  });
});
