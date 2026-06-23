import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { API_CONFIG } from '../api/api.config';

@Component({
  selector: 'app-recover-page',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './recover-page.html',
  styleUrl: './recover-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RecoverPageComponent {
  private readonly formBuilder = inject(FormBuilder);
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly destroyRef = inject(DestroyRef);

  readonly submitting = signal(false);
  readonly sent = signal(false);
  readonly errorMessage = signal('');

  readonly recoverForm = this.formBuilder.nonNullable.group({
    email: ['', [Validators.required, Validators.email]]
  });

  submit() {
    if (this.recoverForm.invalid || this.submitting()) {
      this.recoverForm.markAllAsTouched();
      return;
    }

    this.submitting.set(true);
    this.errorMessage.set('');

    this.http.post<{ ok: boolean; message: string }>(
      `${this.apiConfig.baseUrl}/auth/recover`,
      { email: this.recoverForm.getRawValue().email },
      { withCredentials: true }
    ).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
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
