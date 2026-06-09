import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { TopNavComponent } from '../../../shared/ui/top-nav/top-nav';

@Component({
  selector: 'app-public-shell',
  imports: [TopNavComponent, RouterOutlet],
  templateUrl: './public-shell.html',
  styleUrl: './public-shell.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PublicShellComponent {
  private readonly authService = inject(AuthService);

  readonly currentUser = this.authService.currentUser;

  readonly heroContent = computed(() => {
    const role = this.currentUser()?.primaryRole;

    if (!role || role === 'cliente') {
      return {
        eyebrow: 'Cliente / Viajero',
        title: 'Encuentra estadías que se ven tan bien como se reservan.',
        lede:
          'Explora hoteles, compara ubicaciones, revisa valoraciones y deja listo el espacio para una experiencia visual rica cuando conectemos imágenes reales de propiedades y destinos.',
        cardTitle: 'Marketplace hotelero',
        cardCopy: 'Layout listo para media, reviews, precio y disponibilidad.'
      };
    }

    return {
      eyebrow: 'Exploración / Referencia',
      title: 'Revisa la experiencia pública sin salir de tu espacio de trabajo.',
      lede:
        'Usa esta vista para validar contenido, precios, fichas de hotel y navegación pública con el mismo lenguaje visual que verá el viajero.',
      cardTitle: 'Vista pública de referencia',
      cardCopy: 'Útil para revisar branding, contenido comercial y futura media de hoteles y destinos.'
    };
  });
}
