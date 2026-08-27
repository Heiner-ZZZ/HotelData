import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../../../../../core/auth/auth.service';
import { ToastService } from '../../../../../shared/services/toast.service';
import { ProfileApiService } from '../../../services/profile-api.service';

@Component({
  selector: 'app-profile-password',
  standalone: true,
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    :host .form-section { margin-top: 2rem; }
    :host .password-form {
      display: grid;
      gap: 0.95rem;
    }
    :host .field {
      display: grid;
      gap: 6px;
    }
    :host .field label {
      font-size: 0.75rem;
      font-weight: 600;
      color: var(--muted-text);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    :host .input-wrap {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0 0.65rem;
      border: 1px solid var(--app-border);
      border-radius: 0.5rem;
      background: var(--surface);
      transition: border-color 180ms ease, box-shadow 180ms ease;
    }
    :host .input-wrap:focus-within {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 10%, transparent);
    }
    :host .input-wrap input {
      flex: 1;
      min-height: 38px;
      border: 0;
      background: transparent;
      font-size: 0.88rem;
      outline: none;
    }
    :host .field-error {
      font-size: 0.72rem;
      color: var(--danger);
      margin-top: 2px;
    }
    :host .form-footer {
      margin-top: 0.85rem;
      padding-top: 1.1rem;
      border-top: 1px solid var(--app-border);
      display: flex;
      justify-content: flex-end;
    }
    :host .btn-primary {
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      padding: 0.6rem 1.15rem;
      border: 0;
      border-radius: 0.5rem;
      background: var(--accent);
      color: var(--on-accent);
      font-weight: 600;
      font-size: 0.88rem;
      cursor: pointer;
      transition: opacity 150ms ease, transform 150ms ease;
    }
    :host .btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
    :host .btn-primary:hover:not(:disabled) { opacity: 0.92; }
    :host .notice-success, :host .notice-error {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.75rem 0.85rem;
      border-radius: 0.5rem;
      font-size: 0.84rem;
      margin-bottom: 0.25rem;
    }
    :host .notice-success { background: color-mix(in srgb, var(--success) 10%, transparent); color: var(--success-strong); border: 1px solid color-mix(in srgb, var(--success) 18%, transparent); }
    :host .notice-error { background: color-mix(in srgb, var(--danger) 8%, transparent); color: var(--danger-strong); border: 1px solid color-mix(in srgb, var(--danger) 15%, transparent); }
  `],
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
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly toast = inject(ToastService);

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
          const msg = res.message || 'Contraseña actualizada. Tus otras sesiones han sido cerradas. Inicia sesión nuevamente.';
          this.successMessage.set(msg);
          this.toast.success(msg);
          // RN-O29-03: el backend invalida TODAS las sesiones (incluida la actual).
          // Invalidamos el estado local *inmediatamente* para que top-nav y
          // pp-promotions-tab (gated por isAuthenticated/sessionLoaded) dejen de
          // pollear antes del próximo 401 fantasma; la navegación se retrasa para
          // que el usuario vea el mensaje de éxito.
          this.authService.invalidateSession();
          setTimeout(() => void this.router.navigate(['/login']), 1500);
        },
        error: (err) => {
          this.changingPassword.set(false);
          const detail = err?.error?.detail || err?.detail || 'Error al cambiar la contraseña.';
          this.errorMessage.set(detail);
          this.toast.error(detail);
          setTimeout(() => this.errorMessage.set(''), 6000);
        },
      });
  }
}
