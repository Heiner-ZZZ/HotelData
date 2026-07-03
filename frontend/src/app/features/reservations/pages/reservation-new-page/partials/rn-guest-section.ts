import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-rn-guest-section',
  standalone: true,
  imports: [CurrencyPipe, ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section #guestSection class="surface-card form-section">
      <div class="section-head">
        <span class="material-symbols-outlined section-icon">person</span>
        <div>
          <h2>Datos del huésped</h2>
          @if (isClient()) {
            <p>Información de tu perfil (no editable)</p>
          } @else { <p>Información de contacto del viajero principal</p> }
        </div>
      </div>
      <div class="field-group two-col">
        <label class="field guest-field">
          <span class="field-label">Nombre completo</span>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-prefix">badge</span>
            <input [formControl]="form()?.controls?.guestName" autocomplete="name" [attr.readonly]="isClient() || null" />
          </div>
        </label>
        <label class="field">
          <span class="field-label">Correo electrónico</span>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-prefix">mail</span>
            <input [formControl]="form()?.controls?.guestEmail" type="email" placeholder="ejemplo@correo.com" autocomplete="email"
              [attr.readonly]="isClient() || null" [class.readonly-field]="isClient()" />
          </div>
        </label>
      </div>
      <div class="field-group two-col">
        <label class="field">
          <span class="field-label">Teléfono (opcional)</span>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-prefix">phone</span>
            <input [formControl]="form()?.controls?.guestPhone" type="tel" placeholder="+52 555 123 4567" autocomplete="tel" />
          </div>
        </label>
        <label class="field">
          <span class="field-label">Cédula / Identificación</span>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-prefix">badge</span>
            <input [formControl]="form()?.controls?.cedula" type="text" placeholder="Ej: 123456789" />
          </div>
        </label>
      </div>
    </section>

    <section class="surface-card form-section">
      <div class="section-head">
        <span class="material-symbols-outlined section-icon">room_service</span>
        <div>
          <h2>Peticiones especiales</h2>
          <p>Opciones comunes requeridas por el huésped (sujetas a disponibilidad)</p>
        </div>
      </div>
      <div class="field-group checkbox-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px;">
        @for (req of specialRequestsOptions(); track req.value) {
          <label class="checkbox-label" style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
            <input type="checkbox" (change)="toggleRequest.emit({ request: req.value, checked: $any($event.target).checked })" />
            <span>{{ req.label }}</span>
          </label>
        }
      </div>
    </section>

    @if (selectedHotel()) {
      <section class="surface-card form-section">
        <div class="section-head">
          <span class="material-symbols-outlined section-icon">spa</span>
          <div>
            <h2>Servicios adicionales</h2>
            <p>Amenidades con costo adicional disponibles para tu estancia</p>
          </div>
        </div>
        @if (amenityLoading()) {
          <div class="loading-shade-sm" style="padding: 16px; text-align: center;">
            <span class="material-symbols-outlined loading-spin">sync</span><span>Cargando servicios...</span>
          </div>
        } @else if (amenityCatalog().length > 0) {
          <div class="amenity-selector" style="display: flex; flex-direction: column; gap: 12px;">
            @for (cat of amenityCatalog(); track cat.category) {
              <div>
                <strong style="display: block; margin-bottom: 8px; text-transform: capitalize; color: var(--text-2); font-size: 0.85rem;">{{ cat.category }}</strong>
                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                  @for (item of cat.items; track item.label) {
                    @if (item.active) {
                      <label class="amenity-chip" [class.is-selected]="selectedAmenities().has(item.label)"
                        style="display: flex; align-items: center; gap: 6px; padding: 8px 12px; border: 1px solid var(--border); border-radius: 8px; cursor: pointer;">
                        <input type="checkbox" [checked]="selectedAmenities().has(item.label)"
                          (change)="toggleAmenity.emit(item.label)" style="display: none;" />
                        <span>{{ item.label }}</span>
                        @if (item.unit_price > 0) { <span style="font-weight: 700; color: var(--accent);">{{ item.unit_price | currency:'USD' }}</span> }
                        @else { <span style="color: #16a34a; font-size: 0.8rem;">Gratis</span> }
                      </label>
                    }
                  }
                </div>
              </div>
            }
          </div>
        } @else if (amenityError()) { <p style="color: var(--text-2); font-size: 0.85rem;">{{ amenityError() }}</p> }
        @else { <p style="color: var(--text-2); font-size: 0.85rem;">No hay servicios adicionales disponibles para este hotel.</p> }
      </section>
    }

    <section class="surface-card form-section">
      <div class="section-head">
        <span class="material-symbols-outlined section-icon">notes</span>
        <div>
          <h2>Comentario</h2>
          <p>Requerimientos especiales (opcional)</p>
        </div>
      </div>
      <div class="field-group">
        <label class="field">
          <div class="input-wrap">
            <textarea [formControl]="form()?.controls?.comment" rows="3" placeholder="Ej: Prefiero piso alto, sin mascotas, hora de llegada tardía..."></textarea>
          </div>
        </label>
      </div>
    </section>

    @if (isClient()) {
      <section class="surface-card form-section">
        <div class="section-head">
          <span class="material-symbols-outlined section-icon">local_activity</span>
          <div>
            <h2>Código Promocional</h2>
            <p>¿Tienes un cupón de descuento?</p>
          </div>
        </div>
        <div class="field-group">
          <label class="field">
            <div class="input-wrap promo-wrap" style="display: flex; gap: 8px; border: none; background: transparent; padding: 0;">
              <input [formControl]="form()?.controls?.couponCode" placeholder="Ej: VERANO20" style="text-transform: uppercase; border: 1px solid var(--border-color); padding: 12px 16px; border-radius: 8px; flex: 1; background: var(--surface-1);" />
              <button type="button" class="btn-secondary" (click)="validateCoupon.emit()" [disabled]="couponValidating()">
                @if (couponValidating()) { <span class="material-symbols-outlined loading-spin">sync</span> }
                @else { Aplicar }
              </button>
            </div>
            @if (couponStatus(); as status) {
              <span class="field-message" [style.color]="status.valid ? 'var(--color-success)' : ''" style="margin-top: 8px; display: block; font-weight: 500;">
                {{ status.message }}
                @if (status.valid) { (-{{ status.discountPercent }}%) }
              </span>
            }
          </label>
        </div>
      </section>
    }
  `
})
export class RnGuestSectionComponent {
  readonly form = input<any>(null);
  readonly isClient = input(false);
  readonly selectedHotel = input<any>(null);
  readonly amenityLoading = input(false);
  readonly amenityCatalog = input<any[]>([]);
  readonly amenityError = input<string>('');
  readonly selectedAmenities = input<Set<string>>(new Set());
  readonly couponValidating = input(false);
  readonly couponStatus = input<any>(null);
  readonly specialRequestsOptions = input<any[]>([]);

  readonly toggleRequest = output<{ request: string; checked: boolean }>();
  readonly toggleAmenity = output<string>();
  readonly validateCoupon = output<void>();
}
