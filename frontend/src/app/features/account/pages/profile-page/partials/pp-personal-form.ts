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
          <label for="displayName">Nombre completo</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">badge</span>
            <input id="displayName" type="text" [formControl]="form()?.controls?.displayName" placeholder="Cómo quieres aparecer" />
          </div>
        </div>
        <div class="field">
          <label for="dateOfBirth">Fecha de nacimiento</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">cake</span>
            <input id="dateOfBirth" type="date" [formControl]="form()?.controls?.dateOfBirth" />
          </div>
        </div>
        <div class="field">
          <label for="nationality">Nacionalidad</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">flag</span>
            <input id="nationality" type="text" [formControl]="form()?.controls?.nationality" placeholder="Ej: Mexicana" />
          </div>
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
            <input id="idDocumentNumber" type="text" [formControl]="form()?.controls?.idDocumentNumber" placeholder="Número de identificación" />
          </div>
        </div>
      </div>
    </section>
  `
})
export class PpPersonalFormComponent {
  readonly form = input<any>(null);
  readonly documentTypes = input<any[]>([]);
}
