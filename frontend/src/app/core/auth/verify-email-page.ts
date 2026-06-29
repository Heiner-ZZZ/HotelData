import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { API_CONFIG } from '../api/api.config';

@Component({
  selector: 'app-verify-email-page',
  imports: [RouterLink],
  templateUrl: './verify-email-page.html',
  styleUrl: './verify-email-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class VerifyEmailPageComponent {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly route = inject(ActivatedRoute);

  readonly loading = signal(true);
  readonly success = signal(false);
  readonly message = signal('');

  constructor() {
    const token = this.route.snapshot.queryParamMap.get('token') || '';
    if (!token) {
      this.loading.set(false);
      this.message.set('Enlace inválido. No se encontró el token de verificación.');
      return;
    }
    this.http.get<{ ok: boolean; message: string }>(
      `${this.apiConfig.baseUrl}/account/verify-email`,
      { params: { token }, withCredentials: true }
    ).subscribe({
      next: (res) => {
        this.loading.set(false);
        this.success.set(true);
        this.message.set(res.message || 'Correo verificado exitosamente.');
      },
      error: (error: unknown) => {
        this.loading.set(false);
        if (error instanceof HttpErrorResponse && error.error?.detail) {
          this.message.set(error.error.detail);
        } else {
          this.message.set('Error al verificar el correo. El enlace puede haber expirado.');
        }
      }
    });
  }
}
