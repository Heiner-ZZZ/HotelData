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
            <input id="phone" type="tel" [formControl]="form()?.controls?.phone" placeholder="+52 55 1234 5678" maxlength="20" />
          </div>
          @if (form()?.controls?.phone?.touched && form()?.controls?.phone?.invalid) {
            <span class="field-error"><span class="material-symbols-outlined">error</span>
              @if (form()?.controls?.phone?.hasError('minlength')) { Mínimo 7 caracteres. }
              @else if (form()?.controls?.phone?.hasError('maxlength')) { Máximo 20. }
              @else if (form()?.controls?.phone?.hasError('pattern')) { Solo + al inicio, números, espacios, paréntesis y puntos. El guion - no está permitido. }
            </span>
          }
        </div>
        <div class="field">
          <label for="notificationEmail">Correo de notificaciones</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">mail</span>
            <input id="notificationEmail" type="email" [formControl]="form()?.controls?.notificationEmail" placeholder="notificaciones@ejemplo.com" maxlength="100" />
          </div>
          <p class="field-hint">Correo secundario para recibir alertas y confirmaciones.</p>
          @if (form()?.controls?.notificationEmail?.touched && form()?.controls?.notificationEmail?.invalid) {
            <span class="field-error"><span class="material-symbols-outlined">error</span>
              @if (form()?.controls?.notificationEmail?.hasError('email')) { Ingresá un correo válido. }
              @else if (form()?.controls?.notificationEmail?.hasError('maxlength')) { Máximo 100 caracteres. }
            </span>
          }
        </div>
        <div class="field field-full">
          <label for="addressStreet">Dirección</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">home</span>
            <input id="addressStreet" type="text" [formControl]="form()?.controls?.addressStreet" placeholder="Calle y número" maxlength="100" />
          </div>
          @if (form()?.controls?.addressStreet?.touched && form()?.controls?.addressStreet?.hasError('maxlength')) {
            <span class="field-error"><span class="material-symbols-outlined">error</span> Máximo 100 caracteres.</span>
          }
        </div>
        <div class="field">
          <label for="addressCity">Ciudad</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">location_city</span>
            <input id="addressCity" type="text" [formControl]="form()?.controls?.addressCity" placeholder="Ciudad" maxlength="50" />
          </div>
          @if (form()?.controls?.addressCity?.touched && form()?.controls?.addressCity?.invalid) {
            <span class="field-error"><span class="material-symbols-outlined">error</span>
              @if (form()?.controls?.addressCity?.hasError('maxlength')) { Máximo 50. }
              @else if (form()?.controls?.addressCity?.hasError('pattern')) { Solo letras y espacios. }
            </span>
          }
        </div>
        <div class="field">
          <label for="addressState">Estado / Provincia</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">map</span>
            <input id="addressState" type="text" [formControl]="form()?.controls?.addressState" placeholder="Estado" maxlength="50" />
          </div>
          @if (form()?.controls?.addressState?.touched && form()?.controls?.addressState?.invalid) {
            <span class="field-error"><span class="material-symbols-outlined">error</span>
              @if (form()?.controls?.addressState?.hasError('maxlength')) { Máximo 50. }
              @else if (form()?.controls?.addressState?.hasError('pattern')) { Solo letras y espacios. }
            </span>
          }
        </div>
        <div class="field">
          <label for="addressCountry">País</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">public</span>
            <input id="addressCountry" type="text" [formControl]="form()?.controls?.addressCountry" placeholder="País" maxlength="50" />
          </div>
          @if (form()?.controls?.addressCountry?.touched && form()?.controls?.addressCountry?.invalid) {
            <span class="field-error"><span class="material-symbols-outlined">error</span>
              @if (form()?.controls?.addressCountry?.hasError('maxlength')) { Máximo 50. }
              @else if (form()?.controls?.addressCountry?.hasError('pattern')) { Solo letras y espacios. }
            </span>
          }
        </div>
        <div class="field">
          <label for="addressPostalCode">Código postal</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">mail</span>
            <input id="addressPostalCode" type="text" [formControl]="form()?.controls?.addressPostalCode" placeholder="C.P." maxlength="10" />
          </div>
          @if (form()?.controls?.addressPostalCode?.touched && form()?.controls?.addressPostalCode?.invalid) {
            <span class="field-error"><span class="material-symbols-outlined">error</span>
              @if (form()?.controls?.addressPostalCode?.hasError('maxlength')) { Máximo 10. }
              @else if (form()?.controls?.addressPostalCode?.hasError('pattern')) { Letras, números, espacios y guiones (3-10). }
            </span>
          }
        </div>
      </div>
    </section>
  `
})
export class PpContactFormComponent {
  readonly form = input<any>(null);
}
