import { TestBed } from '@angular/core/testing';

import { GuestsPickerComponent } from './guests-picker';

describe('GuestsPickerComponent', () => {
  function setup(inputs: Partial<{
    adults: number;
    children: number;
    rooms: number;
  }> = {}) {
    TestBed.configureTestingModule({ imports: [GuestsPickerComponent] });
    const fixture = TestBed.createComponent(GuestsPickerComponent);
    for (const [k, v] of Object.entries(inputs)) {
      fixture.componentRef.setInput(k, v);
    }
    fixture.detectChanges();
    return { fixture, comp: fixture.componentInstance };
  }

  it('summarizes guests and rooms in the trigger label', () => {
    const { comp, fixture } = setup({ adults: 2, children: 1, rooms: 2 });
    fixture.detectChanges();
    expect(comp.summaryLabel()).toContain('3');
    expect(comp.summaryLabel()).toContain('2 habitac');
    const el = fixture.nativeElement as HTMLElement;
    expect(el.textContent).toContain('3');
  });

  it('starts closed', () => {
    const { comp } = setup();
    expect(comp.isOpen()).toBe(false);
  });

  it('opens on toggleOpen', () => {
    const { comp } = setup();
    comp.toggleOpen();
    expect(comp.isOpen()).toBe(true);
    comp.toggleOpen();
    expect(comp.isOpen()).toBe(false);
  });

  it('adjusts adults within bounds and emits the new value', () => {
    const { fixture, comp } = setup({ adults: 2 });
    let emitted = 0;
    comp.adultsChange.subscribe((v) => (emitted = v));
    // +1: emit 3 (input sigue en 2 hasta que el padre responda)
    comp.adjust('adults', 1);
    expect(emitted).toBe(3);
    // El padre actualiza el input → el componente re-renderiza con 3
    fixture.componentRef.setInput('adults', emitted);
    fixture.detectChanges();
    // -1 desde 3: emit 2
    comp.adjust('adults', -1);
    expect(emitted).toBe(2);
  });

  it('clamps adults to the minimum of 1', () => {
    const { comp } = setup({ adults: 1 });
    comp.adjust('adults', -1);
    expect(comp.adults()).toBe(1);
  });

  it('clamps rooms to the maximum of 5', () => {
    const { comp } = setup({ rooms: 5 });
    comp.adjust('rooms', 1);
    expect(comp.rooms()).toBe(5);
  });

  it('clamps children to the minimum of 0', () => {
    const { comp } = setup({ children: 0 });
    comp.adjust('children', -1);
    expect(comp.children()).toBe(0);
  });

  it('close() closes the popover', () => {
    const { comp } = setup();
    comp.toggleOpen();
    comp.close();
    expect(comp.isOpen()).toBe(false);
  });
});
