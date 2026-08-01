import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';

import type { RecentGuestView } from './reservation-form.types';

interface GuestAmenityItemView {
  label: string;
  active: boolean;
  unit_price: number;
}

interface GuestAmenityCategoryView {
  category: string;
  items: GuestAmenityItemView[];
}

interface CouponStatusView {
  valid: boolean;
  message: string;
  discountPercent: number;
}

interface SpecialRequestView {
  value: string;
  label: string;
}

@Component({
  selector: 'app-rn-guest-section',
  standalone: true,
  imports: [CurrencyPipe, ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section #guestSection class="surface-card form-section" [formGroup]="form()">
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
            <input formControlName="guestName" autocomplete="name" [attr.readonly]="isClient() || null"
              (input)="guestInput.emit($any($event.target).value)" (focus)="guestFocus.emit()" (blur)="guestBlur.emit()" />
          </div>
        </label>
        <label class="field">
          <span class="field-label">Correo electrónico</span>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-prefix">mail</span>
            <input formControlName="guestEmail" type="email" placeholder="ejemplo@correo.com" autocomplete="email"
              [attr.readonly]="isClient() || null" [class.readonly-field]="isClient()" />
          </div>
        </label>
      </div>
      <div class="field-group two-col">
        <label class="field">
          <span class="field-label">Teléfono <span class="required-mark" aria-hidden="true">*</span></span>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-prefix">phone</span>
            <input formControlName="guestPhone" type="tel" placeholder="+52 555 123 4567" autocomplete="tel" required aria-required="true" />
            @if (form().get('guestPhone')?.touched && form().get('guestPhone')?.hasError('required')) { <span class="field-error-msg">El teléfono es obligatorio.</span> }
          </div>
        </label>
        <label class="field">
          <span class="field-label">Cédula / Identificación <span class="required-mark" aria-hidden="true">*</span></span>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-prefix">badge</span>
            <input formControlName="cedula" type="text" placeholder="Ej: 123456789" autocomplete="off" required aria-required="true" />
            @if (form().get('cedula')?.touched && form().get('cedula')?.hasError('required')) { <span class="field-error-msg">La cédula es obligatoria.</span> }
          </div>
        </label>
      </div>
      @if (!isClient() && showGuestDropdown() && guestSuggestions().length > 0) {
        <div class="recent-guests" role="listbox" aria-label="Contactos recientes">
          <div class="recent-guests-head">
            <span class="material-symbols-outlined">history</span>
            <span>Contactos recientes</span>
          </div>
          @for (guest of guestSuggestions(); track guest.email) {
            <button type="button" class="recent-guest" (mousedown)="$event.preventDefault()" (click)="selectGuest.emit(guest)">
              <span class="material-symbols-outlined">person</span>
              <span class="recent-guest-copy">
                <strong>{{ guest.name }}</strong>
                <small>{{ guest.email }} · {{ guest.phone || 'Sin teléfono' }}</small>
              </span>
              <span class="material-symbols-outlined recent-guest-action">north_west</span>
            </button>
          }
        </div>
      }
    </section>

    <section class="surface-card form-section" [formGroup]="form()">
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
            <input type="checkbox" (change)="onRequestChange(req.value, $event)" />
            <span>{{ req.label }}</span>
          </label>
        }
      </div>
    </section>

    @if (selectedHotel()) {
      <section class="surface-card form-section" [formGroup]="form()">
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
          <div class="amenity-selector">
            @for (cat of amenityCatalog(); track cat.category) {
              <section class="amenity-category">
                <div class="amenity-category-head">
                  <span class="material-symbols-outlined">category</span>
                  <h3>{{ cat.category }}</h3>
                </div>
                <div class="amenity-grid">
                  @for (item of cat.items; track item.label) {
                    <label class="amenity-chip" [class.is-selected]="selectedAmenities().has(item.label)">
                      <input type="checkbox" [checked]="selectedAmenities().has(item.label)"
                        (change)="toggleAmenity.emit(item.label)" />
                      <span class="amenity-check material-symbols-outlined" aria-hidden="true">check_circle</span>
                      <span class="amenity-copy">
                        <span class="amenity-label">{{ item.label }}</span>
                        @if (item.unit_price > 0) { <span class="amenity-price">{{ item.unit_price | currency:'USD' }}</span> }
                        @else { <span class="amenity-free">Gratis</span> }
                      </span>
                    </label>
                  }
                </div>
              </section>
            }
          </div>
        } @else if (amenityError()) { <p style="color: var(--text-2); font-size: 0.85rem;">{{ amenityError() }}</p> }
        @else { <p style="color: var(--text-2); font-size: 0.85rem;">No hay servicios adicionales disponibles para este hotel.</p> }
      </section>
    }

    <section class="surface-card form-section" [formGroup]="form()">
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
            <textarea formControlName="comment" rows="3" placeholder="Ej: Prefiero piso alto, sin mascotas, hora de llegada tardía..."></textarea>
          </div>
        </label>
      </div>
    </section>

    @if (isClient()) {
      <section class="surface-card form-section" [formGroup]="form()">
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
              <input formControlName="couponCode" placeholder="Ej: VERANO20" style="text-transform: uppercase; border: 1px solid var(--border-color); padding: 12px 16px; border-radius: 8px; flex: 1; background: var(--surface-1);" />
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
  readonly form = input.required<FormGroup>();
  readonly isClient = input(false);
  readonly guestSuggestions = input<RecentGuestView[]>([]);
  readonly showGuestDropdown = input(false);
  readonly selectedHotel = input<{ label: string } | null>(null);
  readonly amenityLoading = input(false);
  readonly amenityCatalog = input<GuestAmenityCategoryView[]>([]);
  readonly amenityError = input<string>('');
  readonly selectedAmenities = input<Set<string>>(new Set());
  readonly couponValidating = input(false);
  readonly couponStatus = input<CouponStatusView | null>(null);
  readonly specialRequestsOptions = input<SpecialRequestView[]>([]);

  readonly guestInput = output<string>();
  readonly guestFocus = output<void>();
  readonly guestBlur = output<void>();
  readonly selectGuest = output<RecentGuestView>();
  readonly toggleRequest = output<{ request: string; checked: boolean }>();
  readonly toggleAmenity = output<string>();
  readonly validateCoupon = output<void>();

  onRequestChange(request: string, event: Event): void {
    const checked = (event.target as HTMLInputElement | null)?.checked ?? false;
    this.toggleRequest.emit({ request, checked });
  }
}
