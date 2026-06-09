import { ChangeDetectionStrategy, Component, effect, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-login-redirect-page',
  template: '<p>Redirigiendo al login...</p>',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LoginRedirectPageComponent {
  private readonly route = inject(ActivatedRoute);

  constructor() {
    effect(() => {
      const next = this.route.snapshot.queryParamMap.get('next');
      const target = next ? `/auth/login?next=${encodeURIComponent(next)}` : '/auth/login';
      window.location.href = target;
    });
  }
}
