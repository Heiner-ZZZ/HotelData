import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { HotelOffersComponent } from './hotel-offers';
import type { HotelOfferDto, HotelOffersDto } from '../../models/hotel-detail.dto';

function makeOffer(overrides: Partial<HotelOfferDto> = {}): HotelOfferDto {
  return {
    campaign_id: 'PROMO-1-ABC123',
    title: 'Oferta de verano',
    sent_at_iso: '2026-08-13T10:00:00Z',
    ...overrides,
  };
}

function makeDto(propId: number, items: HotelOfferDto[]): HotelOffersDto {
  return { prop_id: propId, hotel_name: 'Hotel Lima Centro', items };
}

describe('HotelOffersComponent', () => {
  function setup(propId = 1) {
    TestBed.configureTestingModule({
      imports: [HotelOffersComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const fixture = TestBed.createComponent(HotelOffersComponent);
    fixture.componentRef.setInput('propId', propId);
    fixture.detectChanges();
    return {
      fixture,
      component: fixture.componentInstance,
      http: TestBed.inject(HttpTestingController),
    };
  }

  async function seed(
    ctx: { http: HttpTestingController; fixture: { detectChanges(): void; whenStable(): Promise<void> }; component: HotelOffersComponent },
    items: HotelOfferDto[],
  ) {
    ctx.http
      .expectOne(`/api/hotels/${ctx.component.propId()}/promotions`)
      .flush(makeDto(ctx.component.propId(), items));
    await ctx.fixture.whenStable();
    TestBed.flushEffects();
    ctx.fixture.detectChanges();
  }

  it('pide las ofertas activas del hotel por prop_id', async () => {
    const { component, http } = setup(3);
    http.expectOne('/api/hotels/3/promotions');
    expect(component.propId()).toBe(3);
  });

  it('renderiza la sección con título y fecha de cada oferta', async () => {
    const { fixture, component } = setup(1);
    await seed(
      { http: TestBed.inject(HttpTestingController), fixture, component },
      [
        makeOffer({ campaign_id: 'PROMO-1-AAA', title: 'Oferta de verano' }),
        makeOffer({ campaign_id: 'PROMO-1-BBB', title: 'Novedades del spa', sent_at_iso: '2026-08-12T10:00:00Z' }),
      ],
    );

    expect(component.offers()).toHaveLength(2);
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Ofertas y promociones');
    expect(text).toContain('Oferta de verano');
    expect(text).toContain('Novedades del spa');
    expect(text).toContain('2026'); // fecha formateada
  });

  it('no renderiza la sección cuando el hotel no tiene ofertas activas', async () => {
    const { fixture, component } = setup(1);
    await seed({ http: TestBed.inject(HttpTestingController), fixture, component }, []);

    expect(component.offers()).toHaveLength(0);
    expect((fixture.nativeElement as HTMLElement).querySelector('.hotel-offers')).toBeNull();
  });

  it('no dispara request ni renderiza nada sin prop_id', () => {
    const { fixture, http } = setup(0);
    // Sin prop_id no hay request (el recurso devuelve undefined).
    http.expectNone('/api/hotels/0/promotions');
    expect((fixture.nativeElement as HTMLElement).querySelector('.hotel-offers')).toBeNull();
  });

  it('renderiza la oferta de la entidad (Fase 2): descripción pública, código, validez y aplica-a', async () => {
    const { fixture, component } = setup(1);
    await seed(
      { http: TestBed.inject(HttpTestingController), fixture, component },
      [
        makeOffer({
          campaign_id: 'PROMO-1-ENTITY',
          title: 'Oferta exclusiva de verano',
          public_message: '20% de descuento en tarifas Deluxe reservando directo en nuestro sitio.',
          promo_code: 'DELUXE20',
          discount_percent: 20,
          validity: { start_date: '2026-08-01', end_date: '2026-09-30' },
          applies_to_label: 'Deluxe',
          segment_label: 'Familias',
        }),
      ],
    );

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Oferta exclusiva de verano');
    expect(text).toContain('20% de descuento en tarifas Deluxe reservando directo');
    expect(text).toContain('DELUXE20');
    expect(text).toContain('-20%');
    expect(text).toContain('2026-08-01');
    expect(text).toContain('2026-09-30');
    expect(text).toContain('Deluxe');
  });
});
