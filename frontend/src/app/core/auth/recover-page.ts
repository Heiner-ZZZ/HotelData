import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { API_CONFIG } from '../api/api.config';

@Component({
  selector: 'app-recover-page',
  imports: [RouterLink],
  templateUrl: './recover-page.html',
  styleUrls: [
    '../../../styles/_auth-shell.scss',
    '../../../styles/_form-shell.scss',
    './recover-page.scss'
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RecoverPageComponent {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  readonly email = signal('');
  readonly submitting = signal(false);
  readonly sent = signal(false);
  readonly errorMessage = signal('');

  submit(): void {
    const email = this.email().trim();
    if (!email || this.submitting()) return;

    this.submitting.set(true);
    this.errorMessage.set('');

    this.http.post<{ ok: boolean; message: string }>(
      `${this.apiConfig.baseUrl}/auth/recover`,
      { email },
      { withCredentials: true }
    ).subscribe({
      next: () => {
        this.submitting.set(false);
        this.sent.set(true);
      },
      error: () => {
        this.submitting.set(false);
        this.sent.set(true);
      }
    });
  }
}
