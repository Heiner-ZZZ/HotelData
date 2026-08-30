import { CurrencyPipe, DatePipe, UpperCasePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input } from '@angular/core';

interface ReservationPreviewView {
  available: boolean;
  availabilityMessage?: string | null;
  totalPrice: number | null;
  currency: string;
  totalNights: number;
  cancellationPolicy?: string | null;
  priceBreakdown?: {
    ratePlanName: string | null;
    baseNightlyRate: number | null;
    nights: number;
    baseTotal: number | null;
    includedAmenities: { label: string; unitPrice: number }[];
    selectedExtras: { label: string; unitPrice: number }[];
    amenityTotal: number;
    subtotal: number | null;
    taxAmount: number;
    taxRate: number;
    grandTotal: number | null;
  } | null;
}

@Component({
  selector: 'app-rn-review-section',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, UpperCasePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="surface-card review-card">
      <div class="review-card-head">
        <span class="material-symbols-outlined review-icon">description</span>
        <h2>Resumen de solicitud</h2>
      </div>
      <div class="review-grid">
        <div class="review-item">
          <span class="review-label">Hotel</span>
          <strong>{{ selectedHotel()?.label || '—' }}</strong>
        </div>
        <div class="review-item">
          <span class="review-label">Huésped</span>
          <strong>{{ guestName() }}</strong>
        </div>
        <div class="review-item">
          <span class="review-label">Email</span>
          <strong>{{ guestEmail() }}</strong>
        </div>
        @if (guestPhone()) {
          <div class="review-item"><span class="review-label">Teléfono</span><strong>{{ guestPhone() }}</strong></div>
        }
        <div class="review-item">
          <span class="review-label">Entrada</span>
          <strong>{{ checkInDate() | date:'dd/MM/yyyy' }}@if (checkInTime()) { <span class="review-time">a las {{ checkInTime() }}</span> }</strong>
        </div>
        <div class="review-item">
          <span class="review-label">Salida</span>
          <strong>{{ checkOutDate() | date:'dd/MM/yyyy' }}@if (checkOutTime()) { <span class="review-time">a las {{ checkOutTime() }}</span> }</strong>
        </div>
        <div class="review-item">
          <span class="review-label">Estancia</span>
          <strong>{{ nights() }} {{ nights() === 1 ? 'noche' : 'noches' }}</strong>
        </div>
        <div class="review-item">
          <span class="review-label">Ocupación</span>
          <strong>{{ adults() }} adulto(s) · {{ children() }} niño(s) · {{ rooms() }} habitación(es)</strong>
        </div>
        @if (comment()) {
          <div class="review-item review-item-span"><span class="review-label">Comentario</span><strong>{{ comment() }}</strong></div>
        }
        @if (specialRequests().length > 0) {
          <div class="review-item review-item-span">
            <span class="review-label">Peticiones Especiales</span>
            <div class="review-chips">
              @for (req of specialRequests(); track req) {
                <span class="review-chip">
                  <span class="material-symbols-outlined review-chip-icon">check_circle</span>
                  <span class="review-chip-label">{{ req }}</span>
                  @let reqPrice = specialRequestPrices().get(req);
                  @if (reqPrice !== undefined && reqPrice > 0) { <span class="review-chip-price">{{ reqPrice | currency:'USD' }}</span> }
                  @else { <span class="review-chip-free">Gratis</span> }
                </span>
              }
            </div>
          </div>
        }
        @if (selectedAmenities().size > 0) {
          <div class="review-item review-item-span">
            <span class="review-label">Servicios adicionales</span>
            <div class="review-chips">
              @for (item of selectedAmenities(); track item) {
                <span class="review-chip review-chip-amenity">
                  <span class="material-symbols-outlined review-chip-icon">spa</span>
                  <span class="review-chip-label">{{ item }}</span>
                  @let price = amenityPrices().get(item);
                  @if (price !== undefined && price > 0) { <span class="review-chip-price">{{ price | currency:'USD' }}</span> }
                  @else { <span class="review-chip-free">Gratis</span> }
                </span>
              }
            </div>
          </div>
        }
        @if (couponCode() && couponStatus()?.valid) {
          <div class="review-item"><span class="review-label">Cupón</span><strong>{{ couponCode() | uppercase }}</strong></div>
        }
      </div>

      @if (cancellationPolicy()) {
        <div class="review-policy">
          <span class="material-symbols-outlined">policy</span>
          <span>{{ cancellationPolicy() }}</span>
        </div>
      }

      @if (preview(); as p) {
        @if (p.available && p.totalPrice !== null) {
          @if (p.priceBreakdown; as bd) {
            <!-- Price Breakdown with Amenities -->
            <div class="price-breakdown">
              <div class="pb-section">
                <div class="pb-head">
                  <span class="material-symbols-outlined pb-head-icon">bed</span>
                  <span>Tarifa base</span>
                </div>
                @if (bd.ratePlanName) {
                  <div class="pb-plan-name">{{ bd.ratePlanName }}</div>
                }
                <div class="pb-row">
                  <span>{{ bd.baseNightlyRate | currency:p.currency }} × {{ bd.nights }} {{ bd.nights === 1 ? 'noche' : 'noches' }}</span>
                  <span>{{ bd.baseTotal | currency:p.currency }}</span>
                </div>
              </div>

              @if (bd.includedAmenities.length > 0) {
                <div class="pb-section">
                  <div class="pb-head">
                    <span class="material-symbols-outlined pb-head-icon">check_circle</span>
                    <span>Incluidos en el plan</span>
                  </div>
                  @for (item of bd.includedAmenities; track item.label) {
                    <div class="pb-row pb-row-amenity pb-row-included">
                      <span>
                        <span class="material-symbols-outlined pb-amenity-icon">spa</span>
                        {{ item.label }}
                      </span>
                      <span>{{ item.unitPrice | currency:p.currency }}</span>
                    </div>
                  }
                </div>
              }

              @if (bd.selectedExtras.length > 0) {
                <div class="pb-section">
                  <div class="pb-head">
                    <span class="material-symbols-outlined pb-head-icon">add_circle</span>
                    <span>Extras seleccionados</span>
                  </div>
                  @for (item of bd.selectedExtras; track item.label) {
                    <div class="pb-row pb-row-amenity pb-row-extra">
                      <span>
                        <span class="material-symbols-outlined pb-amenity-icon">add</span>
                        {{ item.label }}
                      </span>
                      <span>{{ item.unitPrice | currency:p.currency }}</span>
                    </div>
                  }
                </div>
              }

              <div class="pb-divider"></div>

              <div class="pb-divider"></div>

              <div class="pb-section pb-section-total">
                <div class="pb-row">
                  <span>Subtotal general</span>
                  <span>{{ (bd.subtotal || 0) + bd.amenityTotal | currency:p.currency }}</span>
                </div>
                @if (bd.taxAmount > 0) {
                  <div class="pb-row pb-row-tax">
                    <span>Impuestos ({{ bd.taxRate }}%)</span>
                    <span>{{ bd.taxAmount | currency:p.currency }}</span>
                  </div>
                }
              </div>

              <div class="pb-total">
                <span>Total</span>
                <strong>
                  @let grandTotal = bd.grandTotal;
                  @if (couponStatus(); as coupon) {
                    @if (coupon.valid) {
                      <span class="pb-original">{{ displayGrandTotal(grandTotal, p.totalPrice) | currency:p.currency }}</span>
                      <span>{{ displayGrandTotal(grandTotal, p.totalPrice) * (1 - coupon.discountPercent / 100) | currency:p.currency }}</span>
                    } @else {
                      {{ displayGrandTotal(grandTotal, p.totalPrice) | currency:p.currency }}
                    }
                  } @else {
                    {{ displayGrandTotal(grandTotal, p.totalPrice) | currency:p.currency }}
                  }
                  <span class="pb-night-suffix">({{ p.totalNights }} {{ p.totalNights === 1 ? 'noche' : 'noches' }})</span>
                </strong>
              </div>
            </div>
          } @else {
            <!-- Fallback: simple total without breakdown -->
            <div class="review-total">
              <span>Total estimado</span>
              <strong>
                @if (couponStatus(); as coupon) {
                  @if (coupon.valid) {
                    <span style="text-decoration: line-through; opacity: 0.7; margin-right: 8px; font-weight: normal;">{{ p.totalPrice | currency:p.currency }}</span>
                    <span>{{ p.totalPrice * (1 - coupon.discountPercent / 100) | currency:p.currency }}</span>
                  } @else { {{ p.totalPrice | currency:p.currency }} }
                } @else { {{ p.totalPrice | currency:p.currency }} }
                <span style="font-size: 0.8em; font-weight: normal; margin-left: 4px;">({{ p.totalNights }} {{ p.totalNights === 1 ? 'noche' : 'noches' }})</span>
              </strong>
            </div>
          }
        } @else if (!p.available) {
          <div class="review-total review-total-error">
            <span class="material-symbols-outlined">error</span>
            <strong>{{ p.availabilityMessage || 'Habitación no disponible' }}</strong>
          </div>
        }
      } @else if (previewing()) {
        <div class="review-total"><span class="material-symbols-outlined loading-spin">sync</span><strong>Calculando disponibilidad...</strong></div>
      } @else if (nights() > 0) {
        <div class="review-total"><span>Total de la estancia</span><strong>{{ nights() }} {{ nights() === 1 ? 'noche' : 'noches' }}</strong></div>
      }
    </section>
  `
})
export class RnReviewSectionComponent {
  readonly selectedHotel = input<{ label: string } | null>(null);

  displayGrandTotal(total: number | null, fallback: number | null): number {
    return total ?? fallback ?? 0;
  }
  readonly guestName = input<string>('');
  readonly guestEmail = input<string>('');
  readonly guestPhone = input<string>('');
  readonly checkInDate = input<string>('');
  readonly checkOutDate = input<string>('');
  readonly checkInTime = input<string>('');
  readonly checkOutTime = input<string>('');
  readonly adults = input(0);
  readonly children = input(0);
  readonly rooms = input(1);
  readonly nights = input(0);
  readonly comment = input<string>('');
  readonly specialRequests = input<string[]>([]);
  readonly specialRequestPrices = input<Map<string, number>>(new Map());
  readonly selectedAmenities = input<Set<string>>(new Set());
  readonly amenityPrices = input<Map<string, number>>(new Map());
  readonly couponCode = input<string>('');
  readonly couponStatus = input<{ valid: boolean; discountPercent: number } | null>(null);
  readonly preview = input<ReservationPreviewView | null>(null);
  readonly previewing = input(false);
  readonly cancellationPolicy = input<string | null | undefined>(null);
}
