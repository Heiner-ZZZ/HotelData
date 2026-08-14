import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { ProfileApiService } from '../../../services/profile-api.service';

@Component({
  selector: 'app-profile-password',
  standalone: true,
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  // Mismo ritmo vertical que la caja "Seguridad" (32px de separación entre cards).
  styles: [':host .form-section { margin-top: 2rem; }'],
  template: `
    <section class="form-section">
      <div class="section-header">
        <span class="material-symbols-outlined section-icon">password</span>
        <div>
          <h2>Cambiar contraseña</h2>
          <p>Actualiza tu clave de acceso.</p>
        </div>
      </div>

      <form class="password-form" [formGroup]="passwordForm" (ngSubmit)="submit()">
        @if (successMessage()) {
          <div class="notice-success">
            <span class="material-symbols-outlined">check_circle</span>
            {{ successMessage() }}
          </div>
        }
        @if (errorMessage()) {
          <div class="notice-error">
            <span class="material-symbols-outlined">error</span>
            {{ errorMessage() }}
          </div>
        }

        <div class="field">
          <label for="profileCurrentPassword">Contraseña actual</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">lock</span>
            <input id="profileCurrentPassword" type="password" formControlName="currentPassword"
              placeholder="••••••••" autocomplete="current-password" />
          </div>
          @if (passwordForm.controls.currentPassword.invalid && passwordForm.controls.currentPassword.touched) {
            <span class="field-error">La contraseña actual es obligatoria.</span>
          }
        </div>

        <div class="field">
          <label for="profileNewPassword">Nueva contraseña</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">lock_reset</span>
            <input id="profileNewPassword" type="password" formControlName="newPassword"
              placeholder="Mínimo 8 caracteres" autocomplete="new-password" />
          </div>
          @if (passwordForm.controls.newPassword.invalid && passwordForm.controls.newPassword.touched) {
            <span class="field-error">Mínimo 8 caracteres.</span>
          }
        </div>

        <div class="field">
          <label for="profileConfirmPassword">Confirmar contraseña</label>
          <div class="input-wrap">
            <span class="material-symbols-outlined input-icon">check</span>
            <input id="profileConfirmPassword" type="password" formControlName="confirmPassword"
              placeholder="Repite la nueva" autocomplete="new-password" />
          </div>
          @if (passwordForm.errors?.['mismatch'] && passwordForm.controls.confirmPassword.touched) {
            <span class="field-error">Las contraseñas no coinciden.</span>
          }
        </div>

        <div class="form-footer">
          <button type="submit" class="btn-primary" [disabled]="changingPassword()">
            @if (changingPassword()) {
              <span class="material-symbols-outlined spin">sync</span>
              Cambiando…
            } @else {
              <span class="material-symbols-outlined">vpn_key</span>
              Cambiar contraseña
            }
          </button>
        </div>
      </form>
    </section>
  `
})
export class ProfilePasswordComponent {
  private readonly profileApi = inject(ProfileApiService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  readonly changingPassword = signal(false);
  readonly successMessage = signal('');
  readonly errorMessage = signal('');

  readonly passwordForm = this.formBuilder.nonNullable.group({
    currentPassword: ['', Validators.required],
    newPassword: ['', [Validators.required, Validators.minLength(8)]],
    confirmPassword: ['', Validators.required],
  });

  constructor() {
    this.passwordForm.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        const { newPassword, confirmPassword } = this.passwordForm.getRawValue();
        if (newPassword && confirmPassword && newPassword !== confirmPassword) {
          this.passwordForm.setErrors({ mismatch: true });
        } else if (this.passwordForm.errors?.['mismatch']) {
          const errors = { ...this.passwordForm.errors };
          delete errors['mismatch'];
          this.passwordForm.setErrors(Object.keys(errors).length ? errors : null);
        }
      });
  }

  submit(): void {
    if (this.passwordForm.invalid) {
      this.passwordForm.markAllAsTouched();
      return;
    }

    const { currentPassword, newPassword, confirmPassword } = this.passwordForm.getRawValue();
    if (newPassword !== confirmPassword) {
      this.errorMessage.set('Las contraseñas no coinciden.');
      return;
    }

    this.changingPassword.set(true);
    this.successMessage.set('');
    this.errorMessage.set('');

    this.profileApi.changePassword(currentPassword, newPassword)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.passwordForm.reset();
          this.changingPassword.set(false);
          this.successMessage.set(res.message || 'Contraseña actualizada.');
          setTimeout(() => this.successMessage.set(''), 5000);
        },
        error: (err) => {
          this.changingPassword.set(false);
          this.errorMessage.set(err?.error?.detail || 'Error al cambiar la contraseña.');
          setTimeout(() => this.errorMessage.set(''), 6000);
        },
      });
  }
}
