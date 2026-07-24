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
              <img [src]="preview" alt="Vista previa" class="avatar-img avatar-img--clickable" (click)="onAvatarClick($event)" />
            } @else if (avatarUrl(); as url) {
              <img [src]="url" alt="Avatar" class="avatar-img avatar-img--clickable" (click)="onAvatarClick($event)" />
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
              <svg class="input-icon social-li-svg" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
                <path fill="currentColor" d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
              </svg>
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
  readonly avatarClick = output<void>();

  protected onAvatarClick(event: Event): void {
    event.stopPropagation();
    if (this.uploading()) return;
    this.avatarClick.emit();
  }
}
