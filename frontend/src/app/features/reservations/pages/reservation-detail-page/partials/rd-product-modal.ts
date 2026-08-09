import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-rd-product-modal',
  standalone: true,
  imports: [CurrencyPipe, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (show()) {
      <div class="modal-overlay" (click)="close.emit()">
        <div class="modal-panel product-modal" (click)="$event.stopPropagation()">
          <div class="modal-head">
            <span class="material-symbols-outlined modal-head-icon">shopping_cart</span>
            <div>
              <h2>Agregar servicio</h2>
              <p>Seleccioná un producto para agregar a la reserva</p>
            </div>
            <button type="button" class="modal-close" (click)="close.emit()" aria-label="Cerrar">
              <span class="material-symbols-outlined">close</span>
            </button>
          </div>
          <div class="modal-body">
            @if (productError()) {
              <div class="toast toast-error" style="margin-bottom: 12px;">{{ productError() }}</div>
            }
            @switch (productsState()) {
              @case ('loading') {
                <div class="loading-shade-sm">
                  <span class="material-symbols-outlined loading-spin">sync</span>
                  <span>Cargando productos disponibles...</span>
                </div>
              }
              @case ('error') {
                <div class="error-msg">
                  <span class="material-symbols-outlined">error</span>
                  <span>No se pudieron cargar los productos del hotel.</span>
                </div>
              }
              @case ('forbidden') {
                <div class="error-msg">
                  <span class="material-symbols-outlined">lock</span>
                  <span>Sin permiso para ver los productos del hotel.</span>
                </div>
              }
              @case ('empty') {
                <div class="empty-rooms">
                  <span class="material-symbols-outlined">inventory_2</span>
                  <p>No hay productos disponibles para este hotel.</p>
                  <p class="hint">Configurá los productos en Gestión &gt; Productos.</p>
                </div>
              }
              @case ('success') {
                <div class="product-selector-layout">
                  <div class="ps-products">
                    @if (selectedProduct(); as sp) {
                      <div class="ps-selected-badge">
                        <strong>{{ sp.name }}</strong>
                        <span class="ps-selected-price">{{ sp.unitPrice | currency:'USD' }}</span>
                      </div>
                    } @else {
                      <p class="ps-hint">Seleccioná una categoría para ver productos disponibles</p>
                    }
                    <div class="ps-product-list">
                      @for (prod of filteredProducts(); track prod.productId) {
                        <button type="button" class="ps-product-item"
                          (click)="selectProduct.emit(prod)"
                          [class.is-selected]="addProductId() === prod.productId">
                          <div class="ps-item-info">
                            <strong>{{ prod.name }}</strong>
                            @if (prod.description) { <span class="ps-item-desc">{{ prod.description }}</span> }
                          </div>
                          <span class="ps-item-price">{{ prod.unitPrice | currency:'USD' }}</span>
                        </button>
                      }
                    </div>
                    @if (selectedProduct()) {
                      <div class="qty-selector">
                        <label>
                          <span>Cantidad</span>
                          <div class="qty-controls">
                            <button type="button" (click)="qtyDecrease.emit()" [disabled]="addProductQty() <= 1">
                              <span class="material-symbols-outlined">remove</span>
                            </button>
                            <input type="number" [ngModel]="addProductQty()" (ngModelChange)="qtyChange.emit($event)" min="1" />
                            <button type="button" (click)="qtyIncrease.emit()">
                              <span class="material-symbols-outlined">add</span>
                            </button>
                          </div>
                        </label>
                        @if (selectedProduct(); as sp) {
                          <div class="qty-total">
                            <span>Total:</span>
                            <strong>{{ sp.unitPrice * addProductQty() | currency:'USD' }}</strong>
                          </div>
                        }
                      </div>
                    }
                  </div>
                  <div class="ps-categories">
                    <div class="ps-cat-title">Categorías</div>
                    @for (cat of productCategories(); track cat) {
                      <button type="button" class="ps-cat-item"
                        [class.is-active]="selectedProductCategory() === cat"
                        (click)="selectCategory.emit(cat)">
                        <span class="ps-cat-label">{{ cat }}</span>
                        <span class="ps-cat-count">{{ (productsGrouped().find(g => g.category === cat)?.items ?? []).length }}</span>
                      </button>
                    }
                  </div>
                </div>
              }
            }
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" (click)="close.emit()">Cancelar</button>
            <button type="button" class="btn-primary"
              (click)="addToBooking.emit()"
              [disabled]="addProductSaving() || !selectedProduct()">
              @if (addProductSaving()) {
                <span class="material-symbols-outlined loading-spin">sync</span>
                Agregando...
              } @else {
                <span class="material-symbols-outlined">add_shopping_cart</span>
                Agregar a la reserva
              }
            </button>
          </div>
        </div>
      </div>
    }
  `
})
export class RdProductModalComponent {
  readonly show = input(false);
  readonly productsState = input<string>('idle');
  readonly productsGrouped = input<any[]>([]);
  readonly productCategories = input<string[]>([]);
  readonly selectedProductCategory = input<string>('');
  readonly filteredProducts = input<any[]>([]);
  readonly selectedProduct = input<any>(null);
  readonly addProductId = input<string>('');
  readonly addProductQty = input(1);
  readonly addProductSaving = input(false);
  readonly productError = input<string>('');

  readonly close = output<void>();
  readonly selectCategory = output<string>();
  readonly selectProduct = output<any>();
  readonly qtyDecrease = output<void>();
  readonly qtyIncrease = output<void>();
  readonly qtyChange = output<number>();
  readonly addToBooking = output<void>();
}
