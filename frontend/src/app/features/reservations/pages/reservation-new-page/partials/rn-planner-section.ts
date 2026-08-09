import { CurrencyPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { DateRangePickerComponent } from '../../../../../shared/ui/date-range-picker/date-range-picker';
import { FormGroup } from '@angular/forms';

@Component({
  selector: 'app-rn-planner-section',
  standalone: true,
  imports: [CurrencyPipe, ReactiveFormsModule, DateRangePickerComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="surface-card planner-section" [formGroup]="form()">
      <div class="planner-grid">
        <label class="planner-field" [class.field-error]="false">
          <span class="material-symbols-outlined planner-icon">location_on</span>
          <div class="planner-copy">
            <span class="planner-label">Hotel</span>
            <div class="select-wrap planner-select-wrap">
              <select formControlName="propId" aria-label="Hotel">
                <option [ngValue]="0">¿A dónde quieres ir?</option>
                @for (option of hotelOptions(); track option.propId) {
                  <option [ngValue]="option.propId">{{ option.label }}</option>
                }
              </select>
              <span class="material-symbols-outlined select-arrow">expand_more</span>
            </div>
          </div>
        </label>

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
                  </label>
                  <label class="time-box">
                    <span class="material-symbols-outlined time-box-icon">logout</span>
                    <span class="time-box-label">Salida *</span>
                    <input type="time" formControlName="checkOutTime" class="time-input" required aria-required="true" />
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
            <strong class="planner-value">
              {{ adults() + children() }} persona{{ adults() + children() === 1 ? '' : 's' }},
              {{ rooms() }} habitaci{{ rooms() === 1 ? 'ón' : 'ones' }}
            </strong>
            <div class="planner-steppers">
              <div class="mini-stepper">
                <span class="mini-stepper-label">Adultos</span>
                <div class="stepper">
                  <button type="button" class="stepper-btn" (click)="onAdjust('adults', -1)" [disabled]="adults() <= 1">
                    <span class="material-symbols-outlined">remove</span>
                  </button>
                  <span class="stepper-value">{{ adults() }}</span>
                  <button type="button" class="stepper-btn" (click)="onAdjust('adults', 1)" [disabled]="adults() >= 20">
                    <span class="material-symbols-outlined">add</span>
                  </button>
                </div>
              </div>
              <div class="mini-stepper">
                <span class="mini-stepper-label">Niños</span>
                <div class="stepper">
                  <button type="button" class="stepper-btn" (click)="onAdjust('children', -1)" [disabled]="children() <= 0">
                    <span class="material-symbols-outlined">remove</span>
                  </button>
                  <span class="stepper-value">{{ children() }}</span>
                  <button type="button" class="stepper-btn" (click)="onAdjust('children', 1)" [disabled]="children() >= 10">
                    <span class="material-symbols-outlined">add</span>
                  </button>
                </div>
              </div>
              <div class="mini-stepper">
                <span class="mini-stepper-label">Habitaciones</span>
                <div class="stepper">
                  <button type="button" class="stepper-btn" (click)="onAdjust('rooms', -1)" [disabled]="rooms() <= 1">
                    <span class="material-symbols-outlined">remove</span>
                  </button>
                  <span class="stepper-value">{{ rooms() }}</span>
                  <button type="button" class="stepper-btn" (click)="onAdjust('rooms', 1)" [disabled]="rooms() >= 10">
                    <span class="material-symbols-outlined">add</span>
                  </button>
                </div>
              </div>
            </div>
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
  readonly hotelOptions = input<{ propId: number; label: string }[]>([]);
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
  readonly availabilityInfo = input<{ label: string; icon: string; color: string } | null>(null);
  readonly ratePlans = input<{ ratePlanId: string; name: string; description: string; totalPrice: number; currency: string; avgRatePerNight: number; nights: number }[]>([]);
  readonly ratePlansLoading = input(false);
  readonly selectedRatePlanId = input<string>('');

  readonly startDateChange = output<string>();
  readonly endDateChange = output<string>();
  readonly adjust = output<{ field: string; delta: number }>();
  readonly continueClick = output<void>();
  readonly ratePlanSelect = output<string>();

  onAdjust(field: string, delta: number) {
    this.adjust.emit({ field, delta });
  }
}
