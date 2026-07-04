import { CurrencyPipe, DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({
  selector: 'app-rd-products-section',
  standalone: true,
  imports: [CurrencyPipe, DatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (canAddProducts() && productsState() !== 'loading') {
      <section class="surface-card panel products-panel">
        <div class="panel-head">
          <div class="panel-head-left">
            <span class="material-symbols-outlined panel-icon">shopping_cart</span>
            <h2>Servicios adicionales</h2>
          </div>
          @if (productsState() === 'success' || productsState() === 'empty') {
            <button type="button" class="btn-add-product" (click)="openProductModal.emit()">
              <span class="material-symbols-outlined">add</span>
              Agregar servicio
            </button>
          }
        </div>

        @switch (lineItemsState()) {
          @case ('loading') {
            <div class="products-loading">
              <span class="material-symbols-outlined loading-spin">sync</span>
              <span>Cargando servicios...</span>
            </div>
          }
          @case ('error') { <div class="products-error">Error al cargar servicios adicionales.</div> }
          @case ('empty') { <p class="products-empty">No hay servicios adicionales registrados en esta reserva.</p> }
          @case ('success') {
            <div class="line-items-list">
              @for (item of lineItems(); track item.itemId) {
                <div class="line-item-row">
                  <div class="line-item-info">
                    <div class="line-item-head">
                      <strong>{{ item.name }}</strong>
                      <span class="line-item-qty">x{{ item.quantity }}</span>
                    </div>
                    <div class="line-item-meta">
                      <span>{{ item.unitPrice | currency:'USD' }} c/u</span>
                      <span class="line-item-added">añadido {{ item.addedAt | date:'dd/MM HH:mm' }}</span>
                    </div>
                  </div>
                  <div class="line-item-total-wrap">
                    <span class="line-item-total">{{ item.total | currency:'USD' }}</span>
                    <button type="button" class="btn-remove-li"
                      (click)="removeLineItem.emit({ itemId: item.itemId, itemName: item.name })"
                      [disabled]="removeItemSaving() === item.itemId"
                      aria-label="Eliminar servicio">
                      @if (removeItemSaving() === item.itemId) {
                        <span class="material-symbols-outlined loading-spin">sync</span>
                      } @else {
                        <span class="material-symbols-outlined">close</span>
                      }
                    </button>
                  </div>
                </div>
              }
            </div>
            @if (lineItemsTotal() > 0) {
              <div class="line-items-summary">
                <span>Total servicios adicionales</span>
                <strong>{{ lineItemsTotal() | currency:'USD' }}</strong>
              </div>
            }
          }
        }
      </section>
    }
  `
})
export class RdProductsSectionComponent {
  readonly canAddProducts = input(false);
  readonly productsState = input<string>('idle');
  readonly lineItemsState = input<string>('idle');
  readonly lineItems = input<any[]>([]);
  readonly lineItemsTotal = input(0);
  readonly removeItemSaving = input<string | null>(null);

  readonly openProductModal = output<void>();
  readonly removeLineItem = output<{ itemId: string; itemName: string }>();
}
