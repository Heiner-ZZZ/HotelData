import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-public-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './public-shell.html',
  styleUrl: './public-shell.scss'
})
export class PublicShellComponent {
  readonly navigation = [
    { label: 'Buscar hoteles', href: '/search' },
    { label: 'Reservas', href: '/reservations' },
    { label: 'Panel admin', href: '/admin' }
  ];
}
