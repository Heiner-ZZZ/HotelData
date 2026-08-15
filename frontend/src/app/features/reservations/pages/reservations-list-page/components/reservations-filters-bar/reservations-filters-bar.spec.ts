import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { TestBed } from '@angular/core/testing';

import { ReservationsFiltersBarComponent } from './reservations-filters-bar';

describe('ReservationsFiltersBarComponent (combo de estadía)', () => {
  async function setup(stayStatus = '') {
    const fb = new FormBuilder();
    const stayStatusFilter = jest.fn();

    await TestBed.configureTestingModule({
      imports: [ReactiveFormsModule, ReservationsFiltersBarComponent],
    }).compileComponents();

    const fixture = TestBed.createComponent(ReservationsFiltersBarComponent);
    const component = fixture.componentInstance;

    fixture.componentRef.setInput('dateForm', fb.nonNullable.group({ createdDate: [''] }));
    fixture.componentRef.setInput('currentStayStatusFilter', stayStatus);
    fixture.componentRef.setInput('currentFolioFilter', '');
    fixture.componentRef.setInput('currentSourceFilter', '');
    fixture.componentRef.setInput('hasActiveFilters', false);

    component.stayStatusFilter.subscribe(stayStatusFilter);

    fixture.detectChanges();
    return { fixture, component, stayStatusFilter };
  }

  it('incluye la opción No Show en el combo de estadía (stay_status=no_show)', async () => {
    const { fixture } = await setup();
    const select = fixture.nativeElement.querySelector(
      'select.filter-select',
    ) as HTMLSelectElement;

    const noShow = Array.from(select.options).find((o) => o.value === 'no_show');
    expect(noShow).toBeDefined();
    expect(noShow!.textContent).toContain('No Show');
  });

  it('seleccionar No Show emite stayStatusFilter con "no_show"', async () => {
    const { fixture, stayStatusFilter } = await setup();
    const select = fixture.nativeElement.querySelector(
      'select.filter-select',
    ) as HTMLSelectElement;

    select.value = 'no_show';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();

    expect(stayStatusFilter).toHaveBeenCalledWith('no_show');
  });

  it('deja la opción No Show preseleccionada cuando stay_status=no_show viene en la URL', async () => {
    const { fixture } = await setup('no_show');
    const select = fixture.nativeElement.querySelector(
      'select.filter-select',
    ) as HTMLSelectElement;

    expect(select.value).toBe('no_show');
  });
});
