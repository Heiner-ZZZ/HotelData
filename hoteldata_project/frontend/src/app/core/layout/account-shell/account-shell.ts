import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AccessNavComponent } from '../../../shared/ui/access-nav/access-nav';

@Component({
  selector: 'app-account-shell',
  imports: [AccessNavComponent, RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './account-shell.html',
  styleUrl: './account-shell.scss'
})
export class AccountShellComponent {
  readonly navigation = [
    { label: 'Mis reservas', href: '/account/bookings', icon: 'book_online' },
    { label: 'Nuevo viaje', href: '/account/bookings/new', icon: 'travel_explore' },
    { label: 'Perfil', href: '/account/profile', icon: 'person' }
  ];
}
