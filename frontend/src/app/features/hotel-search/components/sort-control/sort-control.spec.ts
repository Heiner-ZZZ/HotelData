import { TestBed } from '@angular/core/testing';

import { SortControlComponent } from './sort-control';

describe('SortControlComponent — total real y paginación', () => {
  function setup(overrides: Partial<{
    total: number;
    totalPages: number;
    totalIsEstimate: boolean;
    page: number;
    hasNext: boolean;
    hasPrev: boolean;
  }> = {}) {
    TestBed.configureTestingModule({ imports: [SortControlComponent] });
    const fixture = TestBed.createComponent(SortControlComponent);
    fixture.componentRef.setInput('total', overrides.total ?? 1);
    fixture.componentRef.setInput('totalPages', overrides.totalPages ?? 1);
    fixture.componentRef.setInput('totalIsEstimate', overrides.totalIsEstimate ?? false);
    fixture.componentRef.setInput('page', overrides.page ?? 1);
    fixture.componentRef.setInput('hasNext', overrides.hasNext ?? false);
    fixture.componentRef.setInput('hasPrev', overrides.hasPrev ?? false);
    fixture.detectChanges();
    return { fixture };
  }

  it('singulariza el total con un solo hotel', () => {
    const { fixture } = setup({ total: 1 });
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('1 hotel encontrado');
    expect(text).not.toContain('encontrados');
  });

  it('pluraliza con varios hoteles', () => {
    const { fixture } = setup({ total: 5 });
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('5 hoteles encontrados');
  });

  it('sin modo estimado muestra la página real de N', () => {
    const { fixture } = setup({ total: 23, totalPages: 3, page: 2 });
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Página 2 de 3');
    expect(text).not.toContain('hay más resultados');
    expect(text).not.toContain('Disponibilidad real');
  });
});
