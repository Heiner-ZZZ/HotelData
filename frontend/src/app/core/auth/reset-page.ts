import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { API_CONFIG } from '../api/api.config';

@Component({
  selector: 'app-reset-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './reset-page.html',
  styleUrl: './reset-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ResetPageComponent {
  private readonly formBuilder = inject(FormBuilder);
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly submitting = signal(false);
  readonly successMessage = signal('');
  readonly errorMessage = signal('');
  readonly passwordVisible = signal(false);
  readonly token = this.route.snapshot.queryParamMap.get('token') || '';

  readonly resetForm = this.formBuilder.nonNullable.group({
    password: ['', [Validators.required, Validators.minLength(8)]],
    confirm_password: ['', [Validators.required]]
  });

  submit() {
    if (this.resetForm.invalid || this.submitting() || !this.token) {
      this.resetForm.markAllAsTouched();
      return;
    }

    const { password, confirm_password } = this.resetForm.getRawValue();

    if (password !== confirm_password) {
      this.errorMessage.set('Las contraseñas no coinciden.');
      return;
    }

    this.submitting.set(true);
    this.errorMessage.set('');

    this.http.post<{ ok: boolean; message: string }>(
      `${this.apiConfig.baseUrl}/auth/recover/reset`,
      { token: this.token, password },
      { withCredentials: true }
    ).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.submitting.set(false);
        this.successMessage.set('Contraseña restablecida exitosamente.');
        setTimeout(() => this.router.navigate(['/login']), 2000);
      },
      error: (error: unknown) => {
        this.submitting.set(false);
        if (error instanceof HttpErrorResponse && error.error?.detail) {
          this.errorMessage.set(error.error.detail);
        } else {
          this.errorMessage.set('Error al restablecer la contraseña. El enlace puede haber expirado.');
        }
      }
    });
  }

  togglePasswordVisibility() {
    this.passwordVisible.update((v) => !v);
  }
}
