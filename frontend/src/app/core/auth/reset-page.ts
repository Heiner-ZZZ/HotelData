import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { getErrorMessage } from '../../shared/utils/http-error.util';
import { API_CONFIG } from '../api/api.config';

@Component({
  selector: 'app-reset-page',
  imports: [RouterLink],
  templateUrl: './reset-page.html',
  styleUrls: [
    '../../../styles/_auth-shell.scss',
    '../../../styles/_form-shell.scss',
    './reset-page.scss'
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ResetPageComponent {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  readonly password = signal('');
  readonly confirmPassword = signal('');
  readonly submitting = signal(false);
  readonly successMessage = signal('');
  readonly errorMessage = signal('');
  readonly passwordVisible = signal(false);
  readonly token = this.route.snapshot.queryParamMap.get('token') || '';

  submit(): void {
    const pw = this.password();
    const confirm = this.confirmPassword();
    if (!pw || !confirm || this.submitting() || !this.token) return;

    if (pw !== confirm) {
      this.errorMessage.set('Las contraseñas no coinciden.');
      return;
    }

    this.submitting.set(true);
    this.errorMessage.set('');

    this.http.post<{ ok: boolean; message: string }>(
      `${this.apiConfig.baseUrl}/auth/recover/reset`,
      { token: this.token, password: pw },
      { withCredentials: true }
    ).subscribe({
      next: () => {
        this.submitting.set(false);
        this.successMessage.set('Contraseña restablecida exitosamente.');
        setTimeout(() => this.router.navigate(['/login']), 2000);
      },
      error: (error: unknown) => {
        this.submitting.set(false);
        this.errorMessage.set(getErrorMessage(error) || 'Error al restablecer la contraseña. El enlace puede haber expirado.');
      }
    });
  }

  togglePasswordVisibility(): void {
    this.passwordVisible.update((v) => !v);
  }
}
