import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';

import { ProfileSecurityComponent } from '../components/profile-security';
import type { SelectOption } from '../../../models/profile.model';

@Component({
  selector: 'app-pp-preferences-form',
  standalone: true,
  imports: [ReactiveFormsModule, ProfileSecurityComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="form-section">
      <div class="section-header">
        <span class="material-symbols-outlined section-icon">settings</span>
        <div>
          <h2>Preferencias</h2>
          <p>Idioma, notificaciones y comunicaciones.</p>
        </div>
      </div>
      <div class="field-grid">
        <div class="field">
          <label for="preferredLanguage">Idioma preferido</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">language</span>
            <select id="preferredLanguage" [formControl]="form()?.controls?.preferredLanguage">
              @for (opt of languageOptions(); track opt.value) {
                <option [value]="opt.value">{{ opt.label }}</option>
              }
            </select>
          </div>
        </div>
      </div>

      <div class="toggle-group">
        <h3>Notificaciones</h3>
        <label class="toggle-row">
          <div class="toggle-info">
            <span class="material-symbols-outlined toggle-icon">mail</span>
            <div>
              <strong>Notificaciones por correo</strong>
              <p>Recibe confirmaciones, alertas de check-in y ofertas.</p>
            </div>
          </div>
          <input type="checkbox" [formControl]="form()?.controls?.notificationEmailEnabled" class="toggle-input" />
          <span class="toggle-track"></span>
        </label>
        <label class="toggle-row">
          <div class="toggle-info">
            <span class="material-symbols-outlined toggle-icon">sms</span>
            <div>
              <strong>Notificaciones por SMS</strong>
              <p>Alertas importantes en tu teléfono móvil.</p>
            </div>
          </div>
          <input type="checkbox" [formControl]="form()?.controls?.notificationSmsEnabled" class="toggle-input" />
          <span class="toggle-track"></span>
        </label>
        <label class="toggle-row">
          <div class="toggle-info">
            <span class="material-symbols-outlined toggle-icon">campaign</span>
            <div>
              <strong>Comunicaciones comerciales</strong>
              <p>Ofertas, promociones y novedades de hoteles asociados.</p>
            </div>
          </div>
          <input type="checkbox" [formControl]="form()?.controls?.marketingOptIn" class="toggle-input" />
          <span class="toggle-track"></span>
        </label>
      </div>
    </section>

    <app-profile-security />
  `
})
export class PpPreferencesFormComponent {
  readonly form = input<any>(null);
  readonly languageOptions = input<SelectOption[]>([]);
}
