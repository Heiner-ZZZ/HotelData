import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { HttpClient, httpResource } from '@angular/common/http';
import { getErrorStatus, getErrorMessage } from '../../shared/utils/http-error.util';
import { TermsDialogComponent } from '../../shared/ui/terms-dialog/terms-dialog';
import { API_CONFIG } from '../api/api.config';

@Component({
  selector: 'app-register-page',
  imports: [ReactiveFormsModule, RouterLink, TermsDialogComponent],
  templateUrl: './register-page.html',
  styleUrls: [
    '../../../styles/_auth-shell.scss',
    '../../../styles/_form-shell.scss',
    './register-page.scss'
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RegisterPageComponent {
  private readonly formBuilder = inject(FormBuilder);
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly submitting = signal(false);
  readonly successMessage = signal('');
  readonly errorMessage = signal('');
  readonly passwordVisible = signal(false);
  readonly sendVerification = signal(false);

  // ── 2-step verification state ──
  readonly awaitingVerification = signal(false);
  readonly verificationEmail = signal('');
  readonly codeDigits = signal<string[]>(['', '', '', '', '', '']);
  readonly verifyingCode = signal(false);
  readonly codeSent = signal(false);
  readonly sendingCode = signal(false);

  toggleVerification() {
    const newState = !this.sendVerification();
    this.sendVerification.set(newState);

    if (newState) {
      // ── Toggle ON: auto-send verification code if email is valid ──
      this.errorMessage.set('');
      this.successMessage.set('');
      const email = this.registerForm.controls.email.value?.trim().toLowerCase();
      if (email && this.registerForm.controls.email.valid) {
        this.sendVerificationCode();
      } else {
        this.errorMessage.set('Ingresa un correo electrónico válido primero.');
      }
    } else {
      // ── Toggle OFF: reset everything ──
      this.cancelVerification();
    }
  }

  readonly registerForm = this.formBuilder.nonNullable.group({
    username: ['', [Validators.required, Validators.minLength(3)]],
    email: ['', [Validators.required, Validators.email]],
    display_name: [''],
    password: ['', [Validators.required, Validators.minLength(6)]],
    confirm_password: ['', [Validators.required]],
    terms_accepted: [false, [Validators.requiredTrue]],
  });

  // ── Términos y Condiciones (versión activa desde el backend, nunca hardcodeada) ──
  readonly termsOpen = signal(false);
  readonly termsResource = httpResource<{ version: number } | null>(
    () => `${this.apiConfig.baseUrl}/public/legal?doc_type=terms_guest`,
    {
      parse: (dto) => {
        const raw = dto as { version?: number } | null;
        if (!raw || typeof raw.version !== 'number') return null;
        return { version: raw.version };
      },
    },
  );
  readonly termsVersion = (): number | null =>
    this.termsResource.value()?.version ?? null;
  readonly termsLoading = (): boolean => this.termsResource.isLoading();
  readonly termsError = (): boolean => !!this.termsResource.error();

  openTerms(event?: Event): void {
    // El botón vive dentro del <label> del checkbox: no debe alternarlo.
    event?.preventDefault();
    event?.stopPropagation();
    this.termsOpen.set(true);
  }

  closeTerms(): void {
    this.termsOpen.set(false);
  }

  constructor() {
    // Auto-retry when email becomes valid after toggle ON
    this.registerForm.controls.email.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        if (this.sendVerification() && !this.awaitingVerification()) {
          this.errorMessage.set('');
          const email = this.registerForm.controls.email.value?.trim().toLowerCase();
          if (email && this.registerForm.controls.email.valid && !this.sendingCode()) {
            this.sendVerificationCode();
          }
        }
      });
  }

  readonly codeForm = this.formBuilder.nonNullable.group({
    digit0: ['', [Validators.required, Validators.maxLength(1), Validators.pattern('[0-9]')]],
    digit1: ['', [Validators.required, Validators.maxLength(1), Validators.pattern('[0-9]')]],
    digit2: ['', [Validators.required, Validators.maxLength(1), Validators.pattern('[0-9]')]],
    digit3: ['', [Validators.required, Validators.maxLength(1), Validators.pattern('[0-9]')]],
    digit4: ['', [Validators.required, Validators.maxLength(1), Validators.pattern('[0-9]')]],
    digit5: ['', [Validators.required, Validators.maxLength(1), Validators.pattern('[0-9]')]],
  });

  readonly codeControls = [
    this.codeForm.controls.digit0,
    this.codeForm.controls.digit1,
    this.codeForm.controls.digit2,
    this.codeForm.controls.digit3,
    this.codeForm.controls.digit4,
    this.codeForm.controls.digit5,
  ];

  // Auto-advance to next digit on input
  onDigitInput(index: number, event: Event) {
    const input = event.target as HTMLInputElement;
    const digit = input.value.replace(/\D/g, '').slice(0, 1);
    const newDigits = [...this.codeDigits()];
    newDigits[index] = digit;
    this.codeDigits.set(newDigits);

    const controls = this.codeForm.controls;
    controls[`digit${index}` as keyof typeof controls].setValue(digit);

    if (digit && index < 5) {
      const nextInput = document.querySelector<HTMLInputElement>(`#code-digit-${index + 1}`);
      nextInput?.focus();
    }
  }

  onDigitKeydown(index: number, event: KeyboardEvent) {
    if (event.key === 'Backspace' && !this.codeDigits()[index] && index > 0) {
      const prevInput = document.querySelector<HTMLInputElement>(`#code-digit-${index - 1}`);
      prevInput?.focus();
    }
    if (event.key === 'Enter') {
      this.confirmCode();
    }
  }

  onDigitPaste(event: ClipboardEvent) {
    event.preventDefault();
    const text = event.clipboardData?.getData('text') ?? '';
    const digits = text.replace(/\D/g, '').slice(0, 6).split('');
    const newDigits = ['', '', '', '', '', ''];
    digits.forEach((d, i) => { newDigits[i] = d; });
    this.codeDigits.set(newDigits);

    const controls = this.codeForm.controls;
    for (let i = 0; i < 6; i++) {
      controls[`digit${i}` as keyof typeof controls].setValue(newDigits[i]);
    }

    const nextEmpty = newDigits.findIndex(d => !d);
    const focusIndex = nextEmpty >= 0 ? nextEmpty : 5;
    const input = document.querySelector<HTMLInputElement>(`#code-digit-${focusIndex}`);
    input?.focus();
  }

  // ── Email-first flow: send code on email + toggle activation ──

  sendVerificationCode() {
    const email = this.registerForm.controls.email.value?.trim().toLowerCase();
    if (!email || !this.registerForm.controls.email.valid) {
      this.errorMessage.set('Ingresa un correo válido.');
      return;
    }

    this.sendingCode.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    this.http.post<{ ok: boolean; email: string; message: string }>(
      `${this.apiConfig.baseUrl}/auth/send-code`,
      {
        email,
        accepted_terms_version: this.termsVersion() ?? undefined,
      },
      { withCredentials: true }
    ).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (response) => {
        this.sendingCode.set(false);
        // Guard: if toggle was turned OFF while request was in flight, ignore
        if (!this.sendVerification()) return;
        this.codeSent.set(true);
        this.verificationEmail.set(response.email);
        this.successMessage.set(response.message);
        this.awaitingVerification.set(true);
        // Focus first digit input after a short delay
        setTimeout(() => {
          document.querySelector<HTMLInputElement>('#code-digit-0')?.focus();
        }, 100);
      },
      error: (error: unknown) => {
        this.sendingCode.set(false);
        this.errorMessage.set(getErrorMessage(error) || 'Error al enviar el código. Intenta de nuevo.');
      }
    });
  }

  // ── Traditional registration ──

  submit() {
    if (this.sendVerification() && this.registerForm.controls.email.valid) {
      // Email-first flow: send code first, then fill rest of form
      this.sendVerificationCode();
      return;
    }

    if (this.registerForm.invalid || this.submitting()) {
      this.registerForm.markAllAsTouched();
      return;
    }

    if (!this.registerForm.controls.terms_accepted.value) {
      this.errorMessage.set(
        'Debes aceptar los Términos y Condiciones para crear tu cuenta.'
      );
      return;
    }

    const { username, email, display_name, password, confirm_password } = this.registerForm.getRawValue();

    if (password !== confirm_password) {
      this.errorMessage.set('Las contraseñas no coinciden.');
      return;
    }

    this.submitting.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    this.http.post<{ ok: boolean; requires_verification?: boolean; email?: string; message: string }>(
      `${this.apiConfig.baseUrl}/auth/register`,
      {
        username,
        email,
        display_name,
        password,
        send_verification: false,
        accepted_terms_version: this.termsVersion() ?? undefined,
      },
      { withCredentials: true }
    ).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (response) => {
        this.submitting.set(false);
        if (response.requires_verification) {
          this.verificationEmail.set(response.email ?? email);
          this.awaitingVerification.set(true);
          this.successMessage.set(response.message);
        } else {
          this.successMessage.set('Cuenta creada exitosamente. Redirigiendo al login...');
          setTimeout(() => this.router.navigate(['/login']), 1500);
        }
      },
      error: (error: unknown) => {
        this.submitting.set(false);
        if (getErrorStatus(error) === 409) {
          this.errorMessage.set('El usuario o correo ya está registrado.');
        } else {
          this.errorMessage.set(getErrorMessage(error) || 'Error al crear la cuenta. Intenta de nuevo.');
        }
      }
    });
  }

  confirmCode() {
    const code = this.codeDigits().join('');
    if (code.length !== 6) {
      this.errorMessage.set('Ingresa el código completo de 6 dígitos.');
      return;
    }

    const { username, display_name, password } = this.registerForm.getRawValue();

    this.verifyingCode.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    this.http.post<{ ok: boolean; message: string }>(
      `${this.apiConfig.baseUrl}/auth/confirm-code`,
      {
        email: this.verificationEmail(),
        code,
        username,
        password,
        display_name: display_name || undefined,
      },
      { withCredentials: true }
    ).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.verifyingCode.set(false);
        this.successMessage.set('Cuenta verificada exitosamente. Redirigiendo al login...');
        setTimeout(() => this.router.navigate(['/login']), 1500);
      },
      error: (error: unknown) => {
        this.verifyingCode.set(false);
        this.codeDigits.set(['', '', '', '', '', '']);
        const controls = this.codeForm.controls;
        for (let i = 0; i < 6; i++) {
          controls[`digit${i}` as keyof typeof controls].setValue('');
        }
        document.querySelector<HTMLInputElement>('#code-digit-0')?.focus();

        this.errorMessage.set(getErrorMessage(error) || 'Error al verificar el código. Solicita uno nuevo.');
      }
    });
  }

  resendCode() {
    this.sendVerificationCode();
  }

  cancelVerification() {
    this.awaitingVerification.set(false);
    this.codeSent.set(false);
    this.verificationEmail.set('');
    this.codeDigits.set(['', '', '', '', '', '']);
    this.errorMessage.set('');
    this.successMessage.set('');
  }

  togglePasswordVisibility() {
    this.passwordVisible.update((v) => !v);
  }
}
