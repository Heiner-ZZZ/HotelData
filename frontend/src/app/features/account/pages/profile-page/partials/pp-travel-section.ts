import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-pp-travel-section',
  standalone: true,
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="form-section">
      <div class="section-header">
        <span class="material-symbols-outlined section-icon">flight</span>
        <div>
          <h2>Preferencias de viaje</h2>
          <p>Qué tipo de viajero eres y cómo prefieres viajar.</p>
        </div>
      </div>
      <div class="field-grid">
        <div class="field">
          <label for="travelPurpose">Propósito del viaje</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">explore</span>
            <select id="travelPurpose" [formControl]="form()?.controls?.travelPurpose">
              @for (opt of travelPurposeOptions(); track opt.value) {
                <option [value]="opt.value">{{ opt.label }}</option>
              }
            </select>
          </div>
        </div>
        <div class="field">
          <label for="travelBudget">Presupuesto</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">account_balance_wallet</span>
            <select id="travelBudget" [formControl]="form()?.controls?.travelBudget">
              @for (opt of travelBudgetOptions(); track opt.value) {
                <option [value]="opt.value">{{ opt.label }}</option>
              }
            </select>
          </div>
        </div>
        <div class="field">
          <label for="travelCompanions">Acompañantes</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">groups</span>
            <select id="travelCompanions" [formControl]="form()?.controls?.travelCompanions">
              @for (opt of travelCompanionsOptions(); track opt.value) {
                <option [value]="opt.value">{{ opt.label }}</option>
              }
            </select>
          </div>
        </div>
        <div class="field">
          <label for="travelAccommodation">Alojamiento preferido</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">hotel</span>
            <select id="travelAccommodation" [formControl]="form()?.controls?.travelAccommodation">
              @for (opt of travelAccommodationOptions(); track opt.value) {
                <option [value]="opt.value">{{ opt.label }}</option>
              }
            </select>
          </div>
        </div>
        <div class="field">
          <label for="travelDestinationType">Destino favorito</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">landscape</span>
            <select id="travelDestinationType" [formControl]="form()?.controls?.travelDestinationType">
              @for (opt of travelDestinationOptions(); track opt.value) {
                <option [value]="opt.value">{{ opt.label }}</option>
              }
            </select>
          </div>
        </div>
        <div class="field">
          <label for="travelInterests">Intereses (tags)</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">interests</span>
            <input id="travelInterests" type="text" [formControl]="form()?.controls?.travelInterests" placeholder="gastronomía, senderismo, museos…" />
          </div>
        </div>
        <div class="field field-full">
          <label for="travelFrequentFlyer">Programa de viajero frecuente</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">card_membership</span>
            <input id="travelFrequentFlyer" type="text" [formControl]="form()?.controls?.travelFrequentFlyer" placeholder="Ej: Aeroméxico Rewards #12345" />
          </div>
        </div>
        <div class="field field-full">
          <label for="travelLoyaltyPrograms">Programas de lealtad</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">redeem</span>
            <input id="travelLoyaltyPrograms" type="text" [formControl]="form()?.controls?.travelLoyaltyPrograms" placeholder="Ej: Hilton Honors, Marriott Bonvoy" />
          </div>
        </div>
        <div class="field field-full">
          <label for="travelNotes">Notas personales</label>
          <div class="input-wrap textarea-wrap">
            <span class="material-symbols-outlined input-icon">edit_note</span>
            <textarea id="travelNotes" [formControl]="form()?.controls?.travelNotes" placeholder="Preferencias, alergias, requisitos especiales…" rows="3"></textarea>
          </div>
        </div>
      </div>
    </section>
  `
})
export class PpTravelSectionComponent {
  readonly form = input<any>(null);
  readonly travelPurposeOptions = input<any[]>([]);
  readonly travelBudgetOptions = input<any[]>([]);
  readonly travelCompanionsOptions = input<any[]>([]);
  readonly travelAccommodationOptions = input<any[]>([]);
  readonly travelDestinationOptions = input<any[]>([]);
}
