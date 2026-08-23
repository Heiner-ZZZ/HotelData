import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';

import { AuthService } from '../../../../core/auth/auth.service';
import { FavoritesService } from '../../../../core/favorites/favorites.service';
import { TrackingService } from '../../../../core/tracking/tracking.service';
import { HotelCardComponent } from './hotel-card';
import type { HotelSearchResult } from '../../models/hotel-search.model';

function makeHotel(overrides: Partial<HotelSearchResult> = {}): HotelSearchResult {
  return {
    id: 1,
    name: 'Hotel Lima Centro',
    displayName: 'Hotel Lima Centro',
    stars: 4,
    reviewScore: 4.6,
    imageUrl: null,
    destinationLabels: [],
    generalAmenities: [],
    matchedRoomType: null,
    minNightlyRate: 120,
    minNightlyRateLabel: 'S/ 120',
    totalEstimated: null,
    totalEstimatedLabel: null,
    availableRoomTypesCount: null,
    minAvailableRooms: null,
    selected: false,
    ...overrides,
  };
}

describe('HotelCardComponent — galería de imágenes', () => {
  function setup(hotel = makeHotel()) {
    TestBed.configureTestingModule({
      imports: [HotelCardComponent],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        {
          provide: AuthService,
          useValue: { isAuthenticated: () => true, sessionLoaded: () => true },
        },
        {
          provide: FavoritesService,
          useValue: {
            favoriteIds: () => new Set<number>(),
            toggle: jest.fn(),
          },
        },
        {
          provide: TrackingService,
          useValue: { trackHotelClick: jest.fn() },
        },
      ],
    });
    const fixture = TestBed.createComponent(HotelCardComponent);
    fixture.componentRef.setInput('hotel', hotel);
    fixture.detectChanges();
    return { fixture, comp: fixture.componentInstance };
  }

  it('compone la galería con la imagen primaria + 3 placeholders loremflickr', () => {
    const { comp } = setup(makeHotel({ imageUrl: 'https://cdn.example.com/foto.jpg' }));
    const gallery = comp.galleryImages();
    expect(gallery.length).toBe(4);
    expect(gallery[0]).toBe('https://cdn.example.com/foto.jpg');
    expect(gallery.slice(1).every((url) => url.startsWith('https://loremflickr.com/'))).toBe(true);
  });

  it('sin imagen real usa 3 placeholders loremflickr deterministas por hotel', () => {
    const { comp } = setup(makeHotel({ imageUrl: null }));
    const gallery = comp.galleryImages();
    expect(gallery.length).toBe(3);
    expect(gallery.every((url) => url.startsWith('https://loremflickr.com/'))).toBe(true);
  });

  it('renderiza los botones < y > y avanzan/retroceden con wrap', () => {
    const { fixture, comp } = setup();
    fixture.detectChanges();

    const prev = fixture.debugElement.query(By.css('.cc-prev'));
    const next = fixture.debugElement.query(By.css('.cc-next'));
    expect(prev).toBeTruthy();
    expect(next).toBeTruthy();

    next.nativeElement.click();
    fixture.detectChanges();
    expect(comp.currentImageIdx()).toBe(1);

    next.nativeElement.click();
    fixture.detectChanges();
    expect(comp.currentImageIdx()).toBe(2);

    prev.nativeElement.click();
    fixture.detectChanges();
    expect(comp.currentImageIdx()).toBe(1);

    // Wrap: desde la primera, prev va a la última
    comp.goToImage(0);
    fixture.detectChanges();
    prev.nativeElement.click();
    fixture.detectChanges();
    expect(comp.currentImageIdx()).toBe(comp.totalImages() - 1);
  });

  it('muestra un puntito por imagen y el activo sigue el índice', () => {
    const { fixture, comp } = setup();
    fixture.detectChanges();

    const dots = fixture.debugElement.queryAll(By.css('.cc-dot'));
    expect(dots.length).toBe(comp.totalImages());
    expect(dots[0].nativeElement.classList.contains('is-active')).toBe(true);

    comp.goToImage(2);
    fixture.detectChanges();
    expect(dots[2].nativeElement.classList.contains('is-active')).toBe(true);
    expect(dots[0].nativeElement.classList.contains('is-active')).toBe(false);
  });

  it('clic en un puntito navega a esa imagen', () => {
    const { fixture, comp } = setup();
    fixture.detectChanges();

    const dots = fixture.debugElement.queryAll(By.css('.cc-dot'));
    dots[1].nativeElement.click();
    fixture.detectChanges();
    expect(comp.currentImageIdx()).toBe(1);
  });

  it('una imagen que falla se descarta de la galería sin colapsar el carrusel', () => {
    const { comp } = setup(makeHotel({ imageUrl: 'https://cdn.example.com/foto.jpg' }));
    expect(comp.galleryImages().length).toBe(4);

    comp.onImgError({ src: 'https://cdn.example.com/foto.jpg' } as HTMLImageElement);
    expect(comp.galleryImages().length).toBe(3);
    expect(comp.galleryImages().every((u) => u.startsWith('https://loremflickr.com/'))).toBe(true);
  });

  it('no renderiza la descripción hardcodeada del summary', () => {
    const { fixture } = setup(makeHotel({ reviewScore: 4.6, destinationLabels: [] }));
    expect(fixture.nativeElement.querySelector('.summary')).toBeNull();
    const text = fixture.nativeElement.textContent as string;
    expect(text).not.toContain('Disponible para estancias urbanas');
    expect(text).not.toContain('Puntuación 4.6/10');
  });
});

describe('HotelCardComponent — bloque de precio (base + total + disponibles)', () => {
  function setup(hotel = makeHotel(), checkIn = '', checkOut = '') {
    TestBed.configureTestingModule({
      imports: [HotelCardComponent],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        {
          provide: AuthService,
          useValue: { isAuthenticated: () => true, sessionLoaded: () => true },
        },
        {
          provide: FavoritesService,
          useValue: {
            favoriteIds: () => new Set<number>(),
            toggle: jest.fn(),
          },
        },
        {
          provide: TrackingService,
          useValue: { trackHotelClick: jest.fn() },
        },
      ],
    });
    const fixture = TestBed.createComponent(HotelCardComponent);
    fixture.componentRef.setInput('hotel', hotel);
    fixture.componentRef.setInput('checkIn', checkIn);
    fixture.componentRef.setInput('checkOut', checkOut);
    fixture.detectChanges();
    return { fixture, comp: fixture.componentInstance };
  }

  it('calcula las noches entre check-in y check-out', () => {
    const { comp } = setup(makeHotel(), '2026-08-01', '2026-08-04');
    expect(comp.nights()).toBe(3);
  });

  it('sin fechas no hay noches ni total', () => {
    const { comp } = setup(makeHotel());
    expect(comp.nights()).toBeNull();
    expect(comp.displayTotal()).toBeNull();
  });

  it('fechas inválidas no producen total', () => {
    const { comp } = setup(makeHotel(), 'mal', 'peor');
    expect(comp.nights()).toBeNull();
    expect(comp.displayTotal()).toBeNull();
  });

  it('calcula el total = precio base × noches cuando el backend no lo trae', () => {
    const { comp } = setup(makeHotel({ minNightlyRate: 120 }), '2026-08-01', '2026-08-04');
    expect(comp.nights()).toBe(3);
    expect(comp.displayTotal()).toBe(360);
  });

  it('prefiere el total_estimated del backend sobre el cálculo local', () => {
    const { comp } = setup(
      makeHotel({ minNightlyRate: 120, totalEstimated: 330, totalEstimatedLabel: 'S/ 330' }),
      '2026-08-01',
      '2026-08-04',
    );
    expect(comp.displayTotal()).toBe(330);
    expect(comp.displayTotalLabel()).toBe('S/ 330');
  });

  it('muestra el total calculado con fechas y no lo muestra sin fechas', () => {
    const { fixture, comp } = setup(makeHotel({ minNightlyRate: 120 }), '2026-08-01', '2026-08-04');
    fixture.detectChanges();
    expect(comp.displayTotal()).toBe(360);
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('S/ 360');
  });

  it('sin fechas solo muestra el precio base, sin línea de total', () => {
    const { fixture } = setup(makeHotel({ minNightlyRate: 120, minNightlyRateLabel: 'S/ 120' }));
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('S/ 120');
    expect(text).not.toContain('Total');
  });

  it('muestra cuántas quedan a ese precio cuando el backend lo reporta', () => {
    const { fixture, comp } = setup(
      makeHotel({ minNightlyRate: 120, minAvailableRooms: 5 }),
      '2026-08-01',
      '2026-08-04',
    );
    fixture.detectChanges();
    expect(comp.availableRoomsLabel()).toBe('Quedan 5 a este precio');
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Quedan 5');
  });

  it('singulariza el aviso cuando queda una sola habitación', () => {
    const { comp } = setup(makeHotel({ minAvailableRooms: 1 }), '2026-08-01', '2026-08-04');
    expect(comp.availableRoomsLabel()).toBe('Queda 1 a este precio');
  });

  it('sin dato de disponibilidad no renderiza la línea de cuántas quedan', () => {
    const { fixture, comp } = setup(makeHotel(), '2026-08-01', '2026-08-04');
    fixture.detectChanges();
    expect(comp.availableRoomsLabel()).toBeNull();
    const text = fixture.nativeElement.textContent as string;
    expect(text).not.toContain('quedan');
    expect(text).not.toContain('Queda');
  });
});

describe('HotelCardComponent — botón Elegir fechas (patrón Expedia)', () => {
  function setup(hotel = makeHotel(), checkIn = '', checkOut = '', chooseDatesEnabled = false) {
    TestBed.configureTestingModule({
      imports: [HotelCardComponent],
      providers: [
        provideHttpClient(),
        provideRouter([]),
        {
          provide: AuthService,
          useValue: { isAuthenticated: () => true, sessionLoaded: () => true },
        },
        {
          provide: FavoritesService,
          useValue: {
            favoriteIds: () => new Set<number>(),
            toggle: jest.fn(),
          },
        },
        {
          provide: TrackingService,
          useValue: { trackHotelClick: jest.fn() },
        },
      ],
    });
    const fixture = TestBed.createComponent(HotelCardComponent);
    fixture.componentRef.setInput('hotel', hotel);
    fixture.componentRef.setInput('checkIn', checkIn);
    fixture.componentRef.setInput('checkOut', checkOut);
    fixture.componentRef.setInput('chooseDatesEnabled', chooseDatesEnabled);
    fixture.detectChanges();
    return { fixture, comp: fixture.componentInstance };
  }

  it('sin fechas y con chooseDatesEnabled muestra Elegir fechas encima de Ver disponibilidad', () => {
    const { fixture } = setup(makeHotel(), '', '', true);
    const button = fixture.nativeElement.querySelector('.choose-dates-btn');
    expect(button).not.toBeNull();
    expect((button.textContent as string).trim()).toContain('Elegir fechas');
    const primaryLink = fixture.nativeElement.querySelector('a.primary-link');
    expect(primaryLink).not.toBeNull();
    // El botón está ANTES (encima) del enlace Ver disponibilidad en el DOM
    const scoreColumn = fixture.nativeElement.querySelector('.score-column');
    const children = [...scoreColumn.children];
    expect(children.indexOf(button)).toBeLessThan(children.indexOf(primaryLink));
  });

  it('con fechas (total y cantidad visibles) no muestra Elegir fechas', () => {
    const { fixture } = setup(
      makeHotel({ minNightlyRate: 120, minAvailableRooms: 3 }),
      '2026-08-01',
      '2026-08-04',
      true,
    );
    expect(fixture.nativeElement.querySelector('.choose-dates-btn')).toBeNull();
  });

  it('no muestra Elegir fechas cuando chooseDatesEnabled es false (p. ej. favoritos)', () => {
    const { fixture } = setup(makeHotel(), '', '', false);
    expect(fixture.nativeElement.querySelector('.choose-dates-btn')).toBeNull();
  });

  it('emite chooseDates al hacer clic', () => {
    const { fixture, comp } = setup(makeHotel(), '', '', true);
    const emitted = jest.fn();
    comp.chooseDates.subscribe(emitted);
    fixture.nativeElement.querySelector('.choose-dates-btn').click();
    expect(emitted).toHaveBeenCalled();
  });
});
