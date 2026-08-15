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
              <p>Recibe confirmaciones y alertas de check-in.</p>
            </div>
          </div>
          <input type="checkbox" [formControl]="form()?.controls?.notificationEmailEnabled" class="toggle-input" />
          <span class="toggle-track"></span>
        </label>
      </div>

      @if (isGuest()) {
        <div class="toggle-group">
          <h3>Publicidad y promociones</h3>
          <label class="toggle-row">
            <div class="toggle-info">
              <span class="material-symbols-outlined toggle-icon">campaign</span>
              <div>
                <strong>Envío de publicidad, promociones, novedades y ofertas</strong>
                <p>
                  Recibirás publicidad, promociones, novedades y ofertas de los hoteles asociados.
                  Se enviarán a tu correo y a la interfaz principal del huésped, o como notificación.
                </p>
              </div>
            </div>
            <input type="checkbox" [formControl]="form()?.controls?.marketingOptIn" class="toggle-input" />
            <span class="toggle-track"></span>
          </label>
        </div>
      }
    </section>

    <app-profile-security />

    <app-profile-password />
  `
})
export class PpPreferencesFormComponent {
  readonly form = input<any>(null);
  /** Solo los huéspedes (cliente) ven el consentimiento de marketing. */
  readonly isGuest = input(false);
}
