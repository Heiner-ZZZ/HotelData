import { TestBed } from '@angular/core/testing';

import { SeasonalRulesTableComponent, type SeasonalRuleRow } from './seasonal-rules-table';

describe('SeasonalRulesTableComponent', () => {
  const rules: SeasonalRuleRow[] = [
    {
      ruleId: 'SR-1',
      name: 'Temporada alta',
      ratePlanId: 'RP-1',
      startDate: '2026-07-01',
      endDate: '2026-08-31',
      rangeLabel: '2026-07-01 -> 2026-08-31',
      priceOverride: 250,
    },
    {
      ruleId: 'SR-2',
      name: 'Temporada baja',
      ratePlanId: 'RP-1',
      startDate: '2026-11-01',
      endDate: '2026-11-30',
      rangeLabel: '2026-11-01 -> 2026-11-30',
      priceOverride: 120,
    },
  ];

  function setup() {
    TestBed.configureTestingModule({ imports: [SeasonalRulesTableComponent] });
    const fixture = TestBed.createComponent(SeasonalRulesTableComponent);
    const component = fixture.componentInstance;
    fixture.componentRef.setInput('rules', rules);
    fixture.detectChanges();
    return { fixture, component };
  }

  it('does not emit deleteRule immediately when the delete button is clicked', () => {
    const { fixture, component } = setup();
    const emitted: string[] = [];
    component.deleteRule.subscribe((id) => emitted.push(id));

    const deleteButtons = (fixture.nativeElement as HTMLElement).querySelectorAll('.delete-btn');
    (deleteButtons[0] as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(emitted).toEqual([]);
    expect(component.deleteConfirm()).toEqual(rules[0]);
  });

  it('renders the role=alert confirmation with the rule name in the DOM', () => {
    const { fixture, component } = setup();

    component.requestDelete(rules[1]);
    fixture.detectChanges();

    const alert = (fixture.nativeElement as HTMLElement).querySelector('[role="alert"]');
    expect(alert).not.toBeNull();
    expect(alert?.textContent ?? '').toContain('Temporada baja');
    expect(alert?.textContent ?? '').toContain('permanentemente');
  });

  it('emits deleteRule with the ruleId only after confirming', () => {
    const { fixture, component } = setup();
    const emitted: string[] = [];
    component.deleteRule.subscribe((id) => emitted.push(id));

    component.requestDelete(rules[1]);
    fixture.detectChanges();

    const confirmBtn = (fixture.nativeElement as HTMLElement).querySelector('.delete-warning .btn-danger') as HTMLButtonElement;
    confirmBtn.click();
    fixture.detectChanges();

    expect(emitted).toEqual(['SR-2']);
    expect(component.deleteConfirm()).toBeNull();
    expect((fixture.nativeElement as HTMLElement).querySelector('[role="alert"]')).toBeNull();
  });

  it('cancelling clears the confirmation without emitting', () => {
    const { fixture, component } = setup();
    const emitted: string[] = [];
    component.deleteRule.subscribe((id) => emitted.push(id));

    component.requestDelete(rules[0]);
    fixture.detectChanges();

    const cancelBtn = (fixture.nativeElement as HTMLElement).querySelector('.delete-warning .btn-secondary') as HTMLButtonElement;
    cancelBtn.click();
    fixture.detectChanges();

    expect(emitted).toEqual([]);
    expect(component.deleteConfirm()).toBeNull();
    expect((fixture.nativeElement as HTMLElement).querySelector('[role="alert"]')).toBeNull();
  });
});
