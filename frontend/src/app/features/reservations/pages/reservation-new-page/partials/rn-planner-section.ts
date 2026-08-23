import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { ReactiveFormsModule, FormGroup } from '@angular/forms';
import { DateRangePickerComponent } from '../../../../../shared/ui/date-range-picker/date-range-picker';
import { GuestsPickerComponent } from '../../../../../shared/ui/guests-picker/guests-picker';
import { PropertySelectorComponent } from '../../../../../shared/ui/property-selector/property-selector';

import {
  plannerDatesError,
  plannerHotelError,
  plannerOccupancyError,
  plannerTimeError,
} from './reservation-form-messages';

@Component({
  selector: 'app-rn-planner-section',
  standalone: true,
  imports: [CurrencyPipe, ReactiveFormsModule, DateRangePickerComponent, GuestsPickerComponent, PropertySelectorComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="surface-card planner-section" [formGroup]="form()">
      <div class="planner-grid">
        <div class="planner-field" [class.field-error]="plannerHotelError(form().get('propId')) !== null">
          <span class="material-symbols-outlined planner-icon">location_on</span>
          <div class="planner-copy">
            <span class="planner-label">Hotel</span>
            <app-property-selector
              [selectedPropId]="selectedPropId()"
              [selectedLabel]="selectedLabel()"
              (propIdChange)="propertyChange.emit($event)"
            />
            @if (plannerHotelError(form().get('propId')); as err) {
              <span class="field-error-msg" role="alert">{{ err }}</span>
            }
          </div>
        </div>

        <div class="planner-field planner-field--dates">
          <span class="material-symbols-outlined planner-icon">calendar_month</span>
          <div class="planner-copy">
            <span class="planner-label">Fechas</span>
            <div class="planner-dates">
              <app-date-range-picker
                [minDate]="today()"
                [startDate]="checkInDate()"
                [endDate]="checkOutDate()"
                (startChange)="startDateChange.emit($event)"
                (endChange)="endDateChange.emit($event)"
              />
            </div>
            @if (plannerDatesError(form()); as err) {
              <span class="field-error-msg" role="alert">{{ err }}</span>
            }
            @if (checkInDate() && checkOutDate()) {
              <div class="times-section">
                <span class="times-section-label">
                  <span class="material-symbols-outlined">schedule</span>
                  Horario de la estancia <span class="required-mark" aria-hidden="true">*</span>
                </span>
                <span class="times-section-help">Indica cuándo llegarás y cuándo dejarás la habitación. Se valida con el horario del hotel.</span>
                <div class="times-picker">
                  <label class="time-box">
                    <span class="material-symbols-outlined time-box-icon">login</span>
                    <span class="time-box-label">Entrada *</span>
                    <input type="time" formControlName="checkInTime" class="time-input" required aria-required="true" />
                    @if (plannerTimeError(form().get('checkInTime'), 'in'); as err) {
                      <span class="field-error-msg" role="alert">{{ err }}</span>
                    }
                  </label>
                  <label class="time-box">
                    <span class="material-symbols-outlined time-box-icon">logout</span>
                    <span class="time-box-label">Salida *</span>
                    <input type="time" formControlName="checkOutTime" class="time-input" required aria-required="true" />
                    @if (plannerTimeError(form().get('checkOutTime'), 'out'); as err) {
                      <span class="field-error-msg" role="alert">{{ err }}</span>
                    }
                  </label>
                </div>
              </div>
            }
          </div>
        </div>

        <div class="planner-field planner-field--occupancy">
          <span class="material-symbols-outlined planner-icon">person</span>
          <div class="planner-copy">
            <span class="planner-label">Huéspedes</span>
            <!-- Mismo widget compartido que /search y /welcome: el popover de
                 huéspedes y habitaciones (centralización, no dibujo inline). -->
            <app-guests-picker
              [adults]="adults()"
              [children]="children()"
              [rooms]="rooms()"
              (adultsChange)="onGuestsChange('adults', $event)"
              (childrenChange)="onGuestsChange('children', $event)"
              (roomsChange)="onGuestsChange('rooms', $event)"
            />
            @if (plannerOccupancyError(form().get('adults'), 'adults'); as err) {
              <span class="field-error-msg" role="alert">{{ err }}</span>
            }
            @if (plannerOccupancyError(form().get('children'), 'children'); as err) {
              <span class="field-error-msg" role="alert">{{ err }}</span>
            }
            @if (plannerOccupancyError(form().get('rooms'), 'rooms'); as err) {
              <span class="field-error-msg" role="alert">{{ err }}</span>
            }
          </div>
        </div>

        <button type="button" class="planner-cta" (click)="continueClick.emit()">Continuar</button>
      </div>

      @if (selectedHotel(); as hotel) {
        <div class="planner-meta">
          <div class="hotel-chip">
            <span class="material-symbols-outlined">check_circle</span>
            <span>{{ hotel.label }}</span>
          </div>
          @if (preselectedRoomTypeName()) {
            <div class="avail-badge" style="--avail-color: var(--accent)">
              <span class="material-symbols-outlined avail-icon">meeting_room</span>
              <span>{{ preselectedRoomTypeName() }}</span>
            </div>
          }
          @if (preselectedRoomNumber()) {
            <div class="avail-badge" style="--avail-color: var(--success)">
              <span class="material-symbols-outlined avail-icon">door_front</span>
              <span>Habitación {{ preselectedRoomNumber() }} seleccionada</span>
            </div>
          }
          @if (availabilityInfo(); as avail) {
            <div class="avail-badge" [style.--avail-color]="avail.color">
              <span class="material-symbols-outlined avail-icon">{{ avail.icon }}</span>
              <span>{{ avail.label }}</span>
            </div>
            @if (avail.message) {
              <span class="field-error-msg" role="alert">{{ avail.message }}</span>
            }
          }
          @if (computedNights() > 0) {
            <div class="nights-badge">
              <span class="material-symbols-outlined">nights_stay</span>
              <span><strong>{{ computedNights() }}</strong> {{ computedNights() === 1 ? 'noche' : 'noches' }}</span>
            </div>
          }
        </div>

        @if (ratePlans().length > 0) {
          <div class="rate-plan-section">
            <div class="rate-plan-head">
              <span class="material-symbols-outlined rate-plan-head-icon">sell</span>
              <span class="rate-plan-head-label">Elige tu tarifa</span>
              @if (ratePlansLoading()) { <span class="material-symbols-outlined loading-spin">sync</span> }
            </div>
            <div class="rate-plan-grid">
              @for (plan of ratePlans(); track plan.ratePlanId) {
                <label class="rate-plan-card" [class.is-selected]="selectedRatePlanId() === plan.ratePlanId">
                  <input type="radio" name="ratePlan" [value]="plan.ratePlanId"
                    [checked]="selectedRatePlanId() === plan.ratePlanId"
                    (change)="ratePlanSelect.emit(plan.ratePlanId)" style="display: none" />
                  <div class="rate-plan-card-head">
                    <span class="rate-plan-name">{{ plan.name }}</span>
                    <span class="rate-plan-price">{{ plan.totalPrice | currency:plan.currency }}</span>
                  </div>
                  @if (plan.description) { <p class="rate-plan-desc">{{ plan.description }}</p> }
                  <div class="rate-plan-meta">
                    <span class="rate-plan-avg">{{ plan.avgRatePerNight | currency:plan.currency }} /noche</span>
                    <span class="rate-plan-nights">{{ plan.nights }} {{ plan.nights === 1 ? 'noche' : 'noches' }}</span>
                  </div>
                  @if (selectedRatePlanId() === plan.ratePlanId) {
                    <span class="rate-plan-check"><span class="material-symbols-outlined">check_circle</span></span>
                  }
                </label>
              }
            </div>
          </div>
        }
      }
    </section>
  `
})
export class RnPlannerSectionComponent {
  readonly form = input.required<FormGroup>();
  readonly selectedPropId = input(0);
  readonly selectedLabel = input('');
  readonly selectedHotel = input<{ propId: number; label: string } | null>(null);
  readonly preselectedRoomTypeName = input<string>('');
  readonly preselectedRoomNumber = input<string>('');
  readonly today = input<string>('');
  readonly checkInDate = input<string>('');
  readonly checkOutDate = input<string>('');
  readonly adults = input(2);
  readonly children = input(0);
  readonly rooms = input(1);
  readonly computedNights = input(0);
  readonly availabilityInfo = input<{ label: string; icon: string; color: string; message?: string } | null>(null);
  readonly ratePlans = input<{ ratePlanId: string; name: string; description: string; totalPrice: number; currency: string; avgRatePerNight: number; nights: number }[]>([]);
  readonly ratePlansLoading = input(false);
  readonly selectedRatePlanId = input<string>('');

  readonly startDateChange = output<string>();
  readonly endDateChange = output<string>();
  readonly adjust = output<{ field: string; delta: number }>();
  readonly continueClick = output<void>();
  readonly ratePlanSelect = output<string>();
  readonly propertyChange = output<{ propId: number; label: string }>();

  // Helpers de mensajes con acción (expuestos para el template).
  readonly plannerHotelError = plannerHotelError;
  readonly plannerDatesError = plannerDatesError;
  readonly plannerTimeError = plannerTimeError;
  readonly plannerOccupancyError = plannerOccupancyError;

  onAdjust(field: string, delta: number) {
    this.adjust.emit({ field, delta });
  }

  /** GuestsPicker emite el valor NUEVO (absoluto); lo convertimos a delta. */
  onGuestsChange(key: 'adults' | 'children' | 'rooms', value: number): void {
    const current = key === 'adults' ? this.adults() : key === 'children' ? this.children() : this.rooms();
    this.adjust.emit({ field: key, delta: value - current });
  }
}
