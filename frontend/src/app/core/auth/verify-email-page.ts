import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { httpResource } from '@angular/common/http';
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
  private readonly apiConfig = inject(API_CONFIG);
  private readonly route = inject(ActivatedRoute);

  readonly verifyResource = httpResource<{ ok: boolean; message: string }>(() => {
    const token = this.route.snapshot.queryParamMap.get('token') || '';
    if (!token) return undefined;
    return `${this.apiConfig.baseUrl}/account/verify-email?token=${token}`;
  }, {
    withCredentials: true,
  });

  readonly loading = this.verifyResource.isLoading;
  readonly success = computed(() => this.verifyResource.value()?.ok ?? false);
  readonly message = computed(() => {
    if (this.verifyResource.error()) {
      return 'Error al verificar el correo. El enlace puede haber expirado.';
    }
    return this.verifyResource.value()?.message ?? 'Enlace inválido. No se encontró el token de verificación.';
  });
}
