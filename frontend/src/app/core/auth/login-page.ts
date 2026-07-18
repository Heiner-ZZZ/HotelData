import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, DestroyRef, effect, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { AuthService } from './auth.service';

@Component({
  selector: 'app-login-page',
  imports: [RouterLink],
  templateUrl: './login-page.html',
  styleUrl: './login-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LoginPageComponent {
  private readonly authService = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  // ── Form fields as signals (no FormBuilder) ──
  readonly identifier = signal('');
  readonly password = signal('');
  readonly rememberMe = signal(false);

  readonly submitting = signal(false);
  readonly errorMessage = signal('');
  readonly passwordVisible = signal(false);

  constructor() {
    // Remove theme attributes for login page styling, restore on destroy
    const previousTheme = document.documentElement.getAttribute('data-theme');
    document.documentElement.removeAttribute('data-theme');
    inject(DestroyRef).onDestroy(() => {
      if (previousTheme) {
        document.documentElement.setAttribute('data-theme', previousTheme);
      }
    });

    // Redirect if already authenticated (signal-based, replaces ensureSessionLoaded subscription)
    effect(() => {
      if (this.authService.isAuthenticated() && this.authService.sessionLoaded()) {
        const homeHref = this.authService.authState().homeHref;
        void this.router.navigateByUrl(this.authService.resolveDefaultDestination(homeHref));
      }
    });
  }

  submit(): void {
    const id = this.identifier().trim();
    const pw = this.password();
    if (!id || !pw || this.submitting()) return;

    this.submitting.set(true);
    this.errorMessage.set('');

    const nextUrl = this.route.snapshot.queryParamMap.get('next');

    this.authService.login(id, pw, nextUrl, this.rememberMe()).subscribe({
      next: (state) => {
        this.submitting.set(false);
        void this.router.navigateByUrl(this.authService.resolveDefaultDestination(state.homeHref));
      },
      error: (error: unknown) => {
        this.submitting.set(false);
        this.errorMessage.set(this.resolveErrorMessage(error));
      }
    });
  }

  togglePasswordVisibility(): void {
    this.passwordVisible.update((v) => !v);
  }

  private resolveErrorMessage(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      const detail = error.error?.detail;
      if (typeof detail === 'string' && detail.trim()) {
        return detail;
      }
    }
    return 'No pudimos iniciar sesión. Revisa tus credenciales e inténtalo otra vez.';
  }
}
