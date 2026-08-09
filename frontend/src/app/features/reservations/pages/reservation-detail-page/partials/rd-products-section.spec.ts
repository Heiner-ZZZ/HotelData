import { TestBed } from '@angular/core/testing';

import { RdProductsSectionComponent } from './rd-products-section';

describe('RdProductsSectionComponent', () => {
  async function render(inputs: Record<string, unknown>) {
    await TestBed.configureTestingModule({
      imports: [RdProductsSectionComponent],
    }).compileComponents();

    const fixture = TestBed.createComponent(RdProductsSectionComponent);
    for (const [key, value] of Object.entries(inputs)) {
      fixture.componentRef.setInput(key, value);
    }
    fixture.detectChanges();
    return fixture;
  }

  it('muestra el estado "sin permiso" cuando productsState es forbidden', async () => {
    const fixture = await render({
      canAddProducts: false,
      productsState: 'forbidden',
      lineItemsState: 'idle',
      lineItems: [],
    });

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Servicios adicionales');
    expect(text).toContain('Sin permiso');
    expect(text).toContain('properties.read');
  });

  it('no muestra el botón "Agregar servicio" ni los line items en forbidden', async () => {
    const fixture = await render({
      canAddProducts: false,
      productsState: 'forbidden',
      lineItemsState: 'success',
      lineItems: [
        { itemId: 'li-1', name: 'Alquiler de bicicletas', quantity: 1, unitPrice: 10, total: 10, addedAt: '2026-08-08T12:00:00Z' },
      ],
      lineItemsTotal: 10,
    });

    const text = fixture.nativeElement.textContent as string;
    expect(text).not.toContain('Agregar servicio');
    expect(text).not.toContain('Alquiler de bicicletas');
  });

  it('muestra el botón de agregar y los line items cuando hay permiso (regresión)', async () => {
    const fixture = await render({
      canAddProducts: true,
      productsState: 'success',
      lineItemsState: 'success',
      lineItems: [
        { itemId: 'li-1', name: 'Alquiler de bicicletas', quantity: 1, unitPrice: 10, total: 10, addedAt: '2026-08-08T12:00:00Z' },
      ],
      lineItemsTotal: 10,
    });

    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Agregar servicio');
    expect(text).toContain('Alquiler de bicicletas');
    expect(text).toContain('Total servicios adicionales');
  });
});
