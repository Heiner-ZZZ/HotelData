import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-admin-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './admin-shell.html',
  styleUrl: './admin-shell.scss'
})
export class AdminShellComponent {
  readonly navigation = [
    { label: 'Dashboard', href: '/admin' },
    { label: 'Properties', href: '/admin/properties' },
    { label: 'Availability', href: '/admin/availability' }
  ];
}
