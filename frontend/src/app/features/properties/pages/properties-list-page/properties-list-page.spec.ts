import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { signal } from '@angular/core';
import { of } from 'rxjs';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import type { PropertiesDashboardResponseDto } from '../../models/properties.dto';
import { PropertiesListPageComponent } from './properties-list-page';

function buildDashboardDto(total = 1): PropertiesDashboardResponseDto {
  return {
    quick_stats: {
      occupancy_rate: 78,
      occupancy_trend: 4,
      total_revenue_mtd: 3134.4,
      revenue_trend: 12,
      pending_checkins: 1,
      data_health_score: 88,
    },
    revenue_chart: [
      { period: 'Lun', revenue: 100 },
      { period: 'Mar', revenue: 150 },
    ],
    arrivals_today: [
      {
        guest_name: 'Prueba Llegada Tarde',
        initials: 'PL',
        room_type: 'Standard',
        nights: 1,
        arrival_time: '15:00',
        status_tag: 'Standard',
      },
    ],
    properties: {
      items: total
        ? [
            {
              prop_id: 1,
              display_name: 'Hotel Lima Centro',
              country_display_name: 'Perú',
              location: 'Perú',
              prop_starrating: 4,
              review_score_label: '8.0',
              yield_score: 80,
              status: 'Operational',
              sync_status: 'SYNC_ACTIVE',
              sync_latency_ms: 12,
              unit_count: 13,
              performance: {
                source_collection: 'fact_hotel_reservations',
                searches: 10,
                clicks: 5,
                reservations: 13,
                gross_revenue_label: '3,134.40',
                avg_price_label: '212.50',
                review_score_label: '8.0',
                conversion_rate: 1.3,
                click_rate: 50,
              },
            },
          ]
        : [],
      query: '',
      page: 1,
      page_size: 10,
      total,
      total_pages: total ? 1 : 0,
      has_prev: false,
      has_next: false,
      start_index: total ? 1 : 0,
      end_index: total ? 1 : 0,
    },
  };
}

function mockContext(mode: 'all' | 'single' | 'multi' | 'none') {
  return {
    mode: signal(mode),
    ready: signal(true),
    singleHotelMode: signal(mode === 'single'),
    defaultPropId: signal(mode === 'single' ? 7 : 0),
    assignedProperties: signal(
      mode === 'single' ? [{ propId: 7, label: 'Hotel 7' }] : [],
    ),
  };
}

describe('PropertiesListPageComponent — vista reconfigurada y normalizada', () => {
  async function setup(mode: 'all' | 'single' | 'multi' | 'none' = 'multi', total = 1) {
    const navigate = jest.fn();

    await TestBed.configureTestingModule({
      imports: [PropertiesListPageComponent],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { queryParamMap: new Map([['q', '']]) },
            queryParamMap: of(new Map([['q', '']])),
          },
        },
        { provide: Router, useValue: { navigate } },
        { provide: PropertyContextService, useValue: mockContext(mode) },
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(PropertiesListPageComponent);
    fixture.detectChanges();

    const http = TestBed.inject(HttpTestingController);
    http
      .expectOne((r) => r.url.includes('/properties/dashboard'))
      .flush(buildDashboardDto(total));
    // httpResource asienta su valor en un microtask (promise interna) — esperar
    // a que los computeds lo recojan antes de leer el DOM.
    await fixture.whenStable();
    await Promise.resolve();
    fixture.detectChanges();

    return { fixture, navigate, http };
  }

  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
  });

  it('redirige a la propiedad asignada cuando el gerente gobierna un solo hotel', async () => {
    const { navigate } = await setup('single', 1);
    expect(navigate).toHaveBeenCalledWith(['/management/properties', 7], { replaceUrl: true });
  });

  it('muestra la tabla cuando el gerente gobierna más de un hotel', async () => {
    const { fixture } = await setup('multi', 1);
    const table = fixture.nativeElement.querySelector('table') as HTMLTableElement;
    expect(table).toBeTruthy();
    expect(table.classList.contains('data-table')).toBe(true);
    expect(table.textContent).toContain('Hotel Lima Centro');
  });

  it('mantiene la búsqueda y la paginación disponibles', async () => {
    const { fixture } = await setup('multi', 1);
    expect(fixture.nativeElement.querySelector('input[placeholder="Buscar propiedades..."]')).toBeTruthy();
  });

  it('usa el patrón visual estándar surface-card/panel-head', async () => {
    const { fixture } = await setup('multi', 1);
    expect(fixture.nativeElement.querySelector('section.surface-card.data-panel')).toBeTruthy();
    expect(fixture.nativeElement.querySelector('.panel-head h2')?.textContent).toContain('Propiedades');
  });

  it('muestra empty-state cuando no hay propiedades asignadas', async () => {
    const { fixture } = await setup('multi', 0);
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('Sin propiedades asignadas');
    expect(fixture.nativeElement.querySelector('table')).toBeFalsy();
  });

  it('ya no renderiza el gráfico de ingresos con valores inventados', async () => {
    const { fixture } = await setup('multi', 1);
    const text = fixture.nativeElement.textContent;
    expect(text).not.toContain('Rendimiento de Ingresos');
    expect(text).not.toContain('$212.50');
    expect(text).not.toContain('Market Rank');
  });

  it('ya no renderiza los KPI globales ni las llegadas demo', async () => {
    const { fixture } = await setup('multi', 1);
    const text = fixture.nativeElement.textContent;
    expect(text).not.toContain('Tasa de Ocupación');
    expect(text).not.toContain('Llegadas de Hoy');
    expect(text).not.toContain('Prueba Llegada Tarde');
  });
});
