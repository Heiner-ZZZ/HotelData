import { signal } from '@angular/core';
import { HttpResourceRef } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { ProductsAuthService } from '../../services/products-auth.service';
import { ReportApiService } from '../../services/report-api.service';
import type { StockValueReportDto } from '../../models/products-report.dto';
import StockValueReportComponent from './stock-value-report';

/**
 * Known-good literal fixture (independent source of truth, NOT derived
 * from the code under test). Shares: Amenities 9000/12345 ≈ 73%,
 * Lencería 3345/12345 ≈ 27%.
 */
const REPORT: StockValueReportDto = {
  as_of: '2026-08-21T10:30:00Z',
  summary: { total_stock_value: 12345, total_units: 300, distinct_products: 5 },
  by_category: [
    { category: 'Amenities', total_value: 9000, units: 200, products: 3 },
    { category: 'Lencería', total_value: 3345, units: 100, products: 2 },
  ],
  items: [
    {
      id: '68a1',
      product_id: 'PR-001',
      name: 'Shampoo 30ml',
      category: 'Amenities',
      quantity_available: 150,
      cost_price: 20,
      stock_value: 3000,
    },
    {
      id: '68a2',
      product_id: 'PR-002',
      name: 'Sábanas queen',
      category: 'Lencería',
      quantity_available: 50,
      cost_price: 66.9,
      stock_value: 3345,
    },
  ],
};

describe('StockValueReportComponent', () => {
  function fakeReportRef(dto: StockValueReportDto | undefined) {
    return {
      value: signal(dto).asReadonly(),
      isLoading: signal(false).asReadonly(),
      error: signal(undefined).asReadonly(),
      reload: jest.fn(),
    } as unknown as HttpResourceRef<StockValueReportDto | undefined>;
  }

  function setup(opts?: { canSeeCost?: boolean; report?: StockValueReportDto | undefined }) {
    const canSeeCost = signal(opts?.canSeeCost ?? true);
    const ref = fakeReportRef(opts?.report === undefined ? REPORT : opts.report);

    TestBed.configureTestingModule({
      imports: [StockValueReportComponent],
      providers: [
        provideRouter([]),
        {
          provide: PropertyContextService,
          useValue: { currentPropId: signal(1) },
        },
        {
          provide: ProductsAuthService,
          useValue: { canSeeCost },
        },
        {
          provide: ReportApiService,
          useValue: { stockValueReport: jest.fn(() => ref) },
        },
      ],
    });

    const fixture = TestBed.createComponent(StockValueReportComponent);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    return { fixture, component: fixture.componentInstance, el, canSeeCost, ref };
  }

  it('without cost permission shows the lock empty-state and no report content', () => {
    const { el } = setup({ canSeeCost: false });
    expect(el.querySelector('app-empty-state')).not.toBeNull();
    expect(el.querySelector('.hero-card')).toBeNull();
    expect(el.querySelector('.data-section')).toBeNull();
  });

  it('renders the hero with the known-good totals from the fixture', () => {
    const { el } = setup();
    const value = el.querySelector<HTMLElement>('.hero-card__value');
    expect(value?.textContent).toContain('12,345');
    expect(el.querySelector<HTMLElement>('.hero-card__meta')?.textContent).toContain('300');
    expect(el.querySelector<HTMLElement>('.hero-card__meta')?.textContent).toContain('5 productos');
  });

  it('ranks categories descending by value regardless of wire order', () => {
    const unordered: StockValueReportDto = {
      ...REPORT,
      by_category: [
        { category: 'Lencería', total_value: 3345, units: 100, products: 2 },
        { category: 'Amenities', total_value: 9000, units: 200, products: 3 },
        { category: 'Bebidas', total_value: 6000, units: 80, products: 4 },
      ],
    };
    const { component } = setup({ report: unordered });
    expect(component.rankedCategories().map((c) => c.category)).toEqual([
      'Amenities',
      'Bebidas',
      'Lencería',
    ]);
  });

  it('renders category cards in ranked order in the DOM', () => {
    const unordered: StockValueReportDto = {
      ...REPORT,
      by_category: [
        { category: 'Lencería', total_value: 3345, units: 100, products: 2 },
        { category: 'Amenities', total_value: 9000, units: 200, products: 3 },
        { category: 'Bebidas', total_value: 6000, units: 80, products: 4 },
      ],
    };
    const { el } = setup({ report: unordered });
    const names = Array.from(el.querySelectorAll<HTMLElement>('.category-card__name')).map(
      (n) => n.textContent?.trim(),
    );
    expect(names).toEqual(['Amenities', 'Bebidas', 'Lencería']);
  });

  it('renders a capital strip in the hero with one labelled segment per category share', () => {
    const { el } = setup();
    const strip = el.querySelector<HTMLElement>('.capital-strip');
    expect(strip).not.toBeNull();
    const segments = Array.from(strip!.querySelectorAll<HTMLElement>('.capital-strip__segment'));
    expect(segments.length).toBe(2);
    expect(segments[0].style.width).toBe('73%');
    expect(segments[1].style.width).toBe('27%');
    expect(segments[0].getAttribute('title')).toBe('Amenities');
    expect(segments[0].getAttribute('aria-label')).toContain('Amenities');
    expect(segments[0].getAttribute('aria-label')).toContain('73');
  });
});
