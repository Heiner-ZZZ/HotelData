import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { WelcomePageComponent } from './welcome-page';

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
