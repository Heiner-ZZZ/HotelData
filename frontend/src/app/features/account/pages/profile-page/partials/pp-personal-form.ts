import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-pp-personal-form',
  standalone: true,
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="form-section">
      <div class="section-header">
        <span class="material-symbols-outlined section-icon">badge</span>
        <div>
          <h2>Información personal</h2>
          <p>Tu nombre, fecha de nacimiento y documentos de identidad.</p>
        </div>
      </div>
      <div class="field-grid">
        <div class="field">
          <label for="displayName">Nombre completo <span class="required-mark" aria-hidden="true">*</span></label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">badge</span>
            <input id="displayName" type="text" [formControl]="form()?.controls?.displayName" placeholder="Cómo quieres aparecer" maxlength="60" />
          </div>
          @if (form()?.controls?.displayName?.touched && form()?.controls?.displayName?.invalid) {
            <span class="field-error"><span class="material-symbols-outlined">error</span>
              @if (form()?.controls?.displayName?.hasError('required')) { El nombre es obligatorio. }
              @else if (form()?.controls?.displayName?.hasError('minlength')) { Mínimo 2 caracteres. }
              @else if (form()?.controls?.displayName?.hasError('maxlength')) { Máximo 60 caracteres. }
              @else if (form()?.controls?.displayName?.hasError('pattern')) { Solo letras, espacios, guiones y apóstrofes. }
            </span>
          }
        </div>
        <div class="field">
          <label for="dateOfBirth">Fecha de nacimiento</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">cake</span>
            <input id="dateOfBirth" type="date" [formControl]="form()?.controls?.dateOfBirth" />
          </div>
          @if (form()?.controls?.dateOfBirth?.touched && form()?.controls?.dateOfBirth?.hasError('pastDate')) {
            <span class="field-error"><span class="material-symbols-outlined">error</span> Debe ser fecha pasada, menor a 120 años.</span>
          }
        </div>
        <div class="field">
          <label for="nationality">Nacionalidad</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">flag</span>
            <input id="nationality" type="text" [formControl]="form()?.controls?.nationality" placeholder="Ej: Mexicana" maxlength="40" />
          </div>
          @if (form()?.controls?.nationality?.touched && form()?.controls?.nationality?.invalid) {
            <span class="field-error"><span class="material-symbols-outlined">error</span>
              @if (form()?.controls?.nationality?.hasError('minlength')) { Mínimo 2 caracteres. }
              @else if (form()?.controls?.nationality?.hasError('maxlength')) { Máximo 40 caracteres. }
              @else if (form()?.controls?.nationality?.hasError('pattern')) { Solo letras y espacios. }
            </span>
          }
        </div>
        <div class="field">
          <label for="idDocumentType">Tipo de documento</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">badge</span>
            <select id="idDocumentType" [formControl]="form()?.controls?.idDocumentType">
              @for (opt of documentTypes(); track opt.value) {
                <option [value]="opt.value">{{ opt.label }}</option>
              }
            </select>
          </div>
        </div>
        <div class="field">
          <label for="idDocumentNumber">Número de documento</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">pin</span>
            <input id="idDocumentNumber" type="text" [formControl]="form()?.controls?.idDocumentNumber" placeholder="Número de identificación" maxlength="20" />
          </div>
          @if (form()?.controls?.idDocumentNumber?.touched && form()?.controls?.idDocumentNumber?.invalid) {
            <span class="field-error"><span class="material-symbols-outlined">error</span>
              @if (form()?.controls?.idDocumentNumber?.hasError('minlength')) { Mínimo 5 caracteres. }
              @else if (form()?.controls?.idDocumentNumber?.hasError('maxlength')) { Máximo 20. }
              @else if (form()?.controls?.idDocumentNumber?.hasError('pattern')) { Solo letras, números y guiones. }
            </span>
          }
        </div>
      </div>
    </section>
  `
})
export class PpPersonalFormComponent {
  readonly form = input<any>(null);
  readonly documentTypes = input<any[]>([]);
}
