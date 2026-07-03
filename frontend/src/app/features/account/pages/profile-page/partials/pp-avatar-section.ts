import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-pp-avatar-section',
  standalone: true,
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="form-section">
      <div class="section-header">
        <span class="material-symbols-outlined section-icon">travel_explore</span>
        <div>
          <h2>Avatar y redes sociales</h2>
          <p>Tu foto de perfil y enlaces a redes sociales.</p>
        </div>
      </div>

      <div class="avatar-section">
        <div class="avatar-upload-wrapper">
          <div class="avatar-preview" [class.is-uploading]="uploading()">
            @if (uploading()) {
              <div class="upload-progress-ring">
                <svg viewBox="0 0 40 40" class="progress-svg">
                  <circle cx="20" cy="20" r="17" fill="none" stroke="#e5e7eb" stroke-width="3" />
                  <circle cx="20" cy="20" r="17" fill="none" stroke="#1463ff" stroke-width="3"
                    stroke-linecap="round"
                    [attr.stroke-dasharray]="2 * Math.PI * 17"
                    [attr.stroke-dashoffset]="2 * Math.PI * 17 * (1 - uploadProgress() / 100)"
                    transform="rotate(-90 20 20)" />
                </svg>
                <span class="progress-pct">{{ uploadProgress() }}%</span>
              </div>
            } @else if (previewUrl(); as preview) {
              <img [src]="preview" alt="Vista previa" class="avatar-img" />
            } @else if (avatarUrl(); as url) {
              <img [src]="url" alt="Avatar" class="avatar-img" />
            } @else {
              <div class="avatar-placeholder">
                <span class="material-symbols-outlined">person</span>
              </div>
            }
          </div>

          <label class="upload-zone" [class.is-dragover]="dragOver()" [class.is-uploading]="uploading()">
            <input #fileInput type="file" accept="image/jpeg,image/png,image/webp,image/gif,image/avif"
              class="file-input" (change)="onFileSelected.emit($event)" (dragover)="onDragOver.emit($event)"
              (dragleave)="onDragLeave.emit($event)" (drop)="onDrop.emit($event)" [disabled]="uploading()" />
            <span class="material-symbols-outlined upload-icon">cloud_upload</span>
            <strong>Subir foto</strong>
            <span class="upload-hint">Arrastra una imagen o haz clic para seleccionar</span>
            <span class="upload-meta">JPG, PNG, WebP, GIF o AVIF · Máx 5 MB</span>
          </label>
        </div>

        <div class="avatar-or-url">
          <span class="avatar-divider">o</span>
          <div class="avatar-field">
            <label for="avatarUrl">O pega una URL</label>
            <div class="input-wrap">
              <span class="material-symbols-outlined input-icon">link</span>
              <input id="avatarUrl" type="url" [formControl]="form()?.controls?.avatarUrl" placeholder="https://ejemplo.com/mi-foto.jpg" />
            </div>
          </div>
        </div>
      </div>

      <div class="social-section">
        <h3>Redes sociales</h3>
        <div class="field-grid">
          <div class="field">
            <label for="socialInstagram">Instagram</label>
            <div class="input-wrap">
              <span class="material-symbols-outlined input-icon social-ig">camera_alt</span>
              <input id="socialInstagram" type="text" [formControl]="form()?.controls?.socialInstagram" placeholder="&#64;usuario o url" />
            </div>
          </div>
          <div class="field">
            <label for="socialFacebook">Facebook</label>
            <div class="input-wrap">
              <span class="material-symbols-outlined input-icon social-fb">facebook</span>
              <input id="socialFacebook" type="text" [formControl]="form()?.controls?.socialFacebook" placeholder="usuario o url" />
            </div>
          </div>
          <div class="field">
            <label for="socialTwitter">Twitter / X</label>
            <div class="input-wrap">
              <span class="material-symbols-outlined input-icon social-tw">x</span>
              <input id="socialTwitter" type="text" [formControl]="form()?.controls?.socialTwitter" placeholder="&#64;usuario" />
            </div>
          </div>
          <div class="field">
            <label for="socialLinkedin">LinkedIn</label>
            <div class="input-wrap">
              <span class="material-symbols-outlined input-icon social-li">linkedin</span>
              <input id="socialLinkedin" type="text" [formControl]="form()?.controls?.socialLinkedin" placeholder="url del perfil" />
            </div>
          </div>
        </div>
      </div>
    </section>
  `
})
export class PpAvatarSectionComponent {
  protected readonly Math = Math;

  readonly form = input<any>(null);
  readonly uploading = input(false);
  readonly uploadProgress = input(0);
  readonly previewUrl = input<string | null>(null);
  readonly avatarUrl = input<string>('');
  readonly dragOver = input(false);

  readonly onFileSelected = output<Event>();
  readonly onDragOver = output<DragEvent>();
  readonly onDragLeave = output<DragEvent>();
  readonly onDrop = output<DragEvent>();
}
