import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-pp-contact-form',
  standalone: true,
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="form-section">
      <div class="section-header">
        <span class="material-symbols-outlined section-icon">contact_mail</span>
        <div>
          <h2>Información de contacto</h2>
          <p>Teléfono, correo de notificaciones y dirección.</p>
        </div>
      </div>
      <div class="field-grid">
        <div class="field">
          <label for="phone">Teléfono</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">phone</span>
            <input id="phone" type="tel" [formControl]="form()?.controls?.phone" placeholder="+52 55 1234 5678" />
          </div>
        </div>
        <div class="field">
          <label for="notificationEmail">Correo de notificaciones</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">mail</span>
            <input id="notificationEmail" type="email" [formControl]="form()?.controls?.notificationEmail" placeholder="notificaciones@ejemplo.com" />
          </div>
          <p class="field-hint">Correo secundario para recibir alertas y confirmaciones.</p>
        </div>
        <div class="field field-full">
          <label for="addressStreet">Dirección</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">home</span>
            <input id="addressStreet" type="text" [formControl]="form()?.controls?.addressStreet" placeholder="Calle y número" />
          </div>
        </div>
        <div class="field">
          <label for="addressCity">Ciudad</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">location_city</span>
            <input id="addressCity" type="text" [formControl]="form()?.controls?.addressCity" placeholder="Ciudad" />
          </div>
        </div>
        <div class="field">
          <label for="addressState">Estado / Provincia</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">map</span>
            <input id="addressState" type="text" [formControl]="form()?.controls?.addressState" placeholder="Estado" />
          </div>
        </div>
        <div class="field">
          <label for="addressCountry">País</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">public</span>
            <input id="addressCountry" type="text" [formControl]="form()?.controls?.addressCountry" placeholder="País" />
          </div>
        </div>
        <div class="field">
          <label for="addressPostalCode">Código postal</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">mail</span>
            <input id="addressPostalCode" type="text" [formControl]="form()?.controls?.addressPostalCode" placeholder="C.P." />
          </div>
        </div>
      </div>
    </section>
  `
})
export class PpContactFormComponent {
  readonly form = input<any>(null);
}
