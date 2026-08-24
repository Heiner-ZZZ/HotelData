import { mapStrategicHotel, mapStrategicPortfolio } from './strategic-dashboard.mapper';

describe('strategic-dashboard.mapper — hasPrev (comparación vs período anterior)', () => {
  function kpi(overrides: Record<string, unknown> = {}) {
    return {
      id: 'revenue',
      label: 'Revenue neto',
      value: 6100,
      unit: 'USD',
      target: null,
      pct_change: 20.0,
      trend: 'up',
      semaforo: 'green',
      detail: '12 reservas en el período',
      ...overrides,
    };
  }

  it('mapea has_prev=true desde el backend a hasPrev', () => {
    const dto = {
      available: true,
      date_from: '2026-08-01',
      date_to: '2026-08-23',
      prop_id: 1,
      summary: { hoteles: 1, kpis: [kpi({ has_prev: true })] },
    };
    const hotel = mapStrategicHotel(dto);
    expect(hotel.summary.kpis[0].hasPrev).toBe(true);
    expect(hotel.summary.kpis[0].pctChange).toBe(20.0);
  });

  it('mapea has_prev ausente/false a hasPrev=false (sin período anterior)', () => {
    const dto = {
      available: true,
      prop_id: 1,
      summary: { hoteles: 1, kpis: [kpi({ has_prev: false })] },
    };
    const hotel = mapStrategicHotel(dto);
    expect(hotel.summary.kpis[0].hasPrev).toBe(false);
  });

  it('el KPI de cartera (Vista B) también expone hasPrev', () => {
    const dto = {
      available: true,
      summary: { hoteles: 5, kpis: [kpi({ id: 'ocupacion', has_prev: true })] },
    };
    const portfolio = mapStrategicPortfolio(dto);
    expect(portfolio.summary.kpis[0].hasPrev).toBe(true);
  });
});
