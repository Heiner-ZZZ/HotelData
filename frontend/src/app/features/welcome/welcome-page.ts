import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../core/auth/auth.service';

interface WelcomeCategory {
  readonly key: string;
  readonly label: string;
  readonly icon: string;
}

interface WelcomeFeature {
  readonly icon: string;
  readonly title: string;
  readonly description: string;
}

@Component({
  selector: 'app-welcome-page',
  imports: [RouterLink],
  templateUrl: './welcome-page.html',
  styleUrls: [
    '../../../styles/_auth-shell.scss',
    './welcome-page.scss'
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class WelcomePageComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  readonly year = new Date().getFullYear();

  /** Whether the user has an active session — drives the redirect effect below. */
  readonly hasSession = computed(
    () => this.authService.isAuthenticated() && this.authService.sessionLoaded()
  );

  readonly activeCategory = signal<string>('hotels');

  readonly categories = signal<readonly WelcomeCategory[]>([
    { key: 'hotels', label: 'Hoteles', icon: 'hotel' }
  ]);

  readonly features = signal<readonly WelcomeFeature[]>([
    {
      icon: 'event_available',
      title: 'Reservas sin fricción',
      description:
        'Disponibilidad en tiempo real, check-in express y confirmaciones automáticas en cada canal de venta.'
    },
    {
      icon: 'monitoring',
      title: 'Revenue dinámico',
      description:
        'Tarifas ajustadas por demanda, segmento y estacionalidad desde un único panel con datos vivos.'
    },
    {
      icon: 'support_agent',
      title: 'Operación centralizada',
      description:
        'Housekeeping, mantenimiento y huéspedes coordinados desde cualquier dispositivo, en cualquier turno.'
    }
  ]);

  constructor() {
    // Send already-authenticated visitors straight to their default dashboard.
    // Mirrors the pattern used in LoginPageComponent for consistency.
    effect(() => {
      if (this.hasSession()) {
        const homeHref = this.authService.authState().homeHref;
        void this.router.navigateByUrl(this.authService.resolveDefaultDestination(homeHref));
      }
    });
  }

  selectCategory(key: string): void {
    // Visual-only update today; wired up to the search form for future
    // exploration once category-filtered search is enabled.
    this.activeCategory.set(key);
  }
}
