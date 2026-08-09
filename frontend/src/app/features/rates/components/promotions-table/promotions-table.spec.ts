import { TestBed } from '@angular/core/testing';

import { PromotionsTableComponent, type CampaignRow, type CouponRow } from './promotions-table';

describe('PromotionsTableComponent', () => {
  const frozen: CampaignRow = {
    campaignId: 'PC-1-verano',
    name: 'Verano',
    description: 'Verano 2026',
    discountPercent: 15,
    isActive: true,
    startDate: '2026-08-01',
    endDate: '2026-12-31',
    couponTotal: 10,
    couponUsed: 3,
    couponAvailable: 7,
    couponDeleted: 0,
    coupons: [
      { code: 'VERANO2026', activeLabel: 'Sí', campaignId: 'PC-1-verano' },
      { code: 'INVIERNO27', activeLabel: 'No', campaignId: 'PC-1-verano' },
    ],
  };

  const clean: CampaignRow = {
    ...frozen,
    campaignId: 'PC-2-invierno',
    name: 'Invierno',
    couponUsed: 0,
    couponAvailable: 10,
    coupons: [],
  };

  const orphan: CouponRow = { code: 'HUERFANO', activeLabel: 'Sí', campaignId: 'PC-999' };

  function setup() {
    TestBed.configureTestingModule({ imports: [PromotionsTableComponent] });
    const fixture = TestBed.createComponent(PromotionsTableComponent);
    const component = fixture.componentInstance;
    fixture.componentRef.setInput('campaigns', [frozen, clean]);
    fixture.componentRef.setInput('coupons', [orphan]);
    fixture.detectChanges();
    return { fixture, component };
  }

  function rows(fixture: ReturnType<typeof setup>['fixture']): HTMLElement[] {
    return Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('tbody tr')) as HTMLElement[];
  }

  it('renders an explicit Usados column header', () => {
    const { fixture } = setup();
    const headers = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('thead th'))
      .map((th) => th.textContent?.trim());
    expect(headers).toContain('Usados');
  });

  it('marks a campaign with used coupons as frozen with the count', () => {
    const { fixture } = setup();
    const frozenCell = (fixture.nativeElement as HTMLElement)
      .querySelector('tbody tr .coupons-used.frozen');
    expect(frozenCell).not.toBeNull();
    expect(frozenCell?.textContent ?? '').toContain('3');
    // Tooltip que explica el estado congelado.
    expect((frozenCell as HTMLElement).title).toContain('congelada');
  });

  it('shows a neutral 0 for campaigns without used coupons', () => {
    const { fixture } = setup();
    const cells = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('tbody tr .coupons-used'));
    const neutral = cells.find((c) => c.classList.contains('frozen') === false);
    expect(neutral?.textContent?.trim()).toBe('0');
  });

  it('renders each coupon nested right after its campaign row', () => {
    const { fixture } = setup();
    const all = rows(fixture);
    const campaignIdx = all.findIndex((tr) => tr.textContent?.includes('Verano'));
    const couponIdx = all.findIndex((tr) => tr.textContent?.includes('VERANO2026'));
    expect(campaignIdx).toBeGreaterThanOrEqual(0);
    expect(couponIdx).toBe(campaignIdx + 1);
    // La fila de cupón muestra el código y el estado, con guiones en las columnas de campaña.
    const couponRow = all[couponIdx];
    expect(couponRow.classList.contains('coupon-row')).toBe(true);
    expect(couponRow.textContent ?? '').toContain('—');
    expect(couponRow.textContent ?? '').toContain('Activo');
  });

  it('shows the campaign name above its coupon rows so the association is visible', () => {
    const { fixture } = setup();
    const all = rows(fixture);
    const campaignRow = all.find((tr) => tr.textContent?.includes('Verano'));
    // La misma campaña anida sus dos cupones.
    const couponCodes = all
      .filter((tr, i) => campaignRow && i > all.indexOf(campaignRow) && tr.classList.contains('coupon-row'))
      .map((tr) => tr.textContent ?? '');
    expect(couponCodes.some((t) => t.includes('VERANO2026'))).toBe(true);
    expect(couponCodes.some((t) => t.includes('INVIERNO27'))).toBe(true);
  });

  it('uses the normalized edit/delete icon set shared by every rates table', () => {
    const { fixture } = setup();
    const editIcon = (fixture.nativeElement as HTMLElement).querySelector('.edit-btn .material-symbols-outlined');
    const deleteIcon = (fixture.nativeElement as HTMLElement).querySelector('.delete-btn .material-symbols-outlined');
    expect(editIcon?.textContent?.trim()).toBe('edit');
    expect(deleteIcon?.textContent?.trim()).toBe('delete');
  });

  it('renders coupons without a matching campaign under a "sin campaña" group header', () => {
    const { fixture } = setup();
    const all = rows(fixture);
    const header = all.find((tr) => tr.textContent?.includes('sin campaña'));
    expect(header).toBeDefined();
    const headerIdx = all.indexOf(header as HTMLElement);
    const orphanIdx = all.findIndex((tr) => tr.textContent?.includes('HUERFANO'));
    expect(orphanIdx).toBeGreaterThan(headerIdx);
  });
});
