import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-account-shell',
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './account-shell.html',
  styleUrl: './account-shell.scss'
})
export class AccountShellComponent {
  readonly navigation = [
    { label: 'Mis reservas', href: '/account/bookings' },
    { label: 'Nuevo viaje', href: '/account/bookings/new' },
    { label: 'Perfil', href: '/account/profile' }
  ];
}
