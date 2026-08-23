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

  it('cada hotel destacado muestra una galería con puntitos (diseño tipo comparador)', async () => {
    TestBed.configureTestingModule({
      imports: [WelcomePageComponent],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    const fixture = TestBed.createComponent(WelcomePageComponent);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();

    http
      .expectOne((r) => r.url.includes('/hotels/availability'))
      .flush({
        items: [
          {
            prop_id: 1,
            display_name: 'Hotel Lima Centro',
            prop_starrating: 4,
            prop_review_score: 8.5,
            image_url: null,
            destination_labels: ['Lima'],
            min_nightly_rate_label: 'S/ 120',
          },
        ],
      });
    http
      .expectOne((r) => r.url.includes('/public/currencies'))
      .flush({ currencies: [] });
    await fixture.whenStable();
    fixture.detectChanges();

    // La galería del welcome genera 3 variantes (hotel / lobby / pool) → 3 puntitos.
    const cards = fixture.nativeElement.querySelectorAll('.hotel-card');
    const imgs = fixture.nativeElement.querySelectorAll('.welcome-gallery__img');
    expect(cards.length).toBe(1);
    expect(imgs.length).toBe(3);
    const dots = fixture.nativeElement.querySelectorAll('.cc-dot');
    expect(dots.length).toBe(3);
    expect(dots[0].classList.contains('is-active')).toBe(true);

    // Clic en el segundo puntito lo activa (sin navegar, es un <a>).
    dots[1].dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
    fixture.detectChanges();
    const dotsAfter = fixture.nativeElement.querySelectorAll('.cc-dot');
    expect(dotsAfter[1].classList.contains('is-active')).toBe(true);
    expect(dotsAfter[0].classList.contains('is-active')).toBe(false);
  });

  it('muestra flechas prev/next en la galería y navegan con wrap-around (sin navegar el <a>)', async () => {
    TestBed.configureTestingModule({
      imports: [WelcomePageComponent],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    const fixture = TestBed.createComponent(WelcomePageComponent);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();

    http
      .expectOne((r) => r.url.includes('/hotels/availability'))
      .flush({
        items: [
          {
            prop_id: 1,
            display_name: 'Hotel Lima Centro',
            prop_starrating: 4,
            prop_review_score: 8.5,
            image_url: null,
            destination_labels: ['Lima'],
            min_nightly_rate_label: 'S/ 120',
          },
        ],
      });
    http
      .expectOne((r) => r.url.includes('/public/currencies'))
      .flush({ currencies: [] });
    await fixture.whenStable();
    fixture.detectChanges();

    const card = fixture.nativeElement.querySelector('.hotel-card') as HTMLElement;
    const prev = card.querySelector('.cc-prev') as HTMLButtonElement;
    const next = card.querySelector('.cc-next') as HTMLButtonElement;
    expect(prev).toBeTruthy();
    expect(next).toBeTruthy();

    const isActive = () =>
      Array.from(card.querySelectorAll('.cc-dot')).findIndex(d => d.classList.contains('is-active'));

    // Siguiente: 0 → 1 → 2 → 0 (wrap).
    next.click();
    fixture.detectChanges();
    expect(isActive()).toBe(1);
    next.click();
    fixture.detectChanges();
    expect(isActive()).toBe(2);
    next.click();
    fixture.detectChanges();
    expect(isActive()).toBe(0);

    // Anterior con wrap desde la primera: 0 → 2.
    prev.click();
    fixture.detectChanges();
    expect(isActive()).toBe(2);

    // El clic en las flechas no navegó (el card es un <a>): seguimos en el welcome.
    expect(fixture.nativeElement.querySelector('.welcome-featured')).toBeTruthy();
  });

  /** Monta el welcome con un hotel destacado (3 fotos) y flushea la API. */
  async function renderOneHotel() {
    TestBed.configureTestingModule({
      imports: [WelcomePageComponent],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    });
    const fixture = TestBed.createComponent(WelcomePageComponent);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http
      .expectOne((r) => r.url.includes('/hotels/availability'))
      .flush({
        items: [
          {
            prop_id: 1,
            display_name: 'Hotel Lima Centro',
            prop_starrating: 4,
            prop_review_score: 8.5,
            image_url: null,
            destination_labels: ['Lima'],
            min_nightly_rate_label: 'S/ 120',
          },
        ],
      });
    http
      .expectOne((r) => r.url.includes('/public/currencies'))
      .flush({ currencies: [] });
    await fixture.whenStable();
    fixture.detectChanges();
    return fixture;
  }

  it('rota la galería sola con el mouse sobre la card y se detiene al salir (con wrap)', async () => {
    const fixture = await renderOneHotel();
    const comp = fixture.componentInstance;

    jest.useFakeTimers();
    comp.startRotation(1);
    expect(comp.welcomeSlide(1)).toBe(0);

    jest.advanceTimersByTime(3500);
    expect(comp.welcomeSlide(1)).toBe(1);
    jest.advanceTimersByTime(3500);
    expect(comp.welcomeSlide(1)).toBe(2);
    jest.advanceTimersByTime(3500);
    expect(comp.welcomeSlide(1)).toBe(0); // wrap → primera foto

    // Al salir se detiene y vuelve a la primera foto (como el hotel-card).
    comp.stopRotation(1);
    jest.advanceTimersByTime(3500 * 3);
    expect(comp.welcomeSlide(1)).toBe(0);
    jest.useRealTimers();
  });

  it('respeta prefers-reduced-motion: no inicia la rotación', async () => {
    const fixture = await renderOneHotel();
    const comp = fixture.componentInstance;
    const original = window.matchMedia;
    window.matchMedia = jest.fn().mockImplementation((query: string) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    })) as unknown as typeof window.matchMedia;

    jest.useFakeTimers();
    comp.startRotation(1);
    jest.advanceTimersByTime(3500 * 3);
    expect(comp.welcomeSlide(1)).toBe(0); // nunca avanzó
    jest.useRealTimers();
    window.matchMedia = original;
  });

  it('mouseenter arranca la rotación y mouseleave la detiene y resetea (template)', async () => {
    const fixture = await renderOneHotel();
    const comp = fixture.componentInstance;
    const card = fixture.nativeElement.querySelector('.hotel-card') as HTMLElement;
    const dots = () =>
      Array.from(card.querySelectorAll('.cc-dot')).findIndex(d => d.classList.contains('is-active'));
    const controls = card.querySelector('app-carousel-controls') as HTMLElement;

    jest.useFakeTimers();
    card.dispatchEvent(new MouseEvent('mouseenter', { bubbles: false }));
    fixture.detectChanges();
    expect(dots()).toBe(0);
    // Hover de la card → revela las flechas del carrusel compartido.
    expect(controls.classList.contains('revealed')).toBe(true);

    jest.advanceTimersByTime(3500);
    fixture.detectChanges();
    expect(dots()).toBe(1);

    card.dispatchEvent(new MouseEvent('mouseleave', { bubbles: false }));
    fixture.detectChanges();
    expect(controls.classList.contains('revealed')).toBe(false);
    jest.advanceTimersByTime(3500 * 3);
    fixture.detectChanges();
    expect(dots()).toBe(0); // detenido y reseteado
    jest.useRealTimers();
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
