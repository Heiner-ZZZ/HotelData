import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';

import { ProfilePasswordComponent } from '../components/profile-password';
import { ProfileSecurityComponent } from '../components/profile-security';

@Component({
  selector: 'app-pp-preferences-form',
  standalone: true,
  imports: [ReactiveFormsModule, ProfilePasswordComponent, ProfileSecurityComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="form-section">
      <div class="section-header">
        <span class="material-symbols-outlined section-icon">settings</span>
        <div>
          <h2>Preferencias</h2>
          <p>Notificaciones y comunicaciones.</p>
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

    <app-profile-password />
  `
})
export class PpPreferencesFormComponent {
  readonly form = input<any>(null);
}
