import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-system-admin-shell',
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './system-admin-shell.html',
  styleUrl: './system-admin-shell.scss'
})
export class SystemAdminShellComponent {
  readonly navigation = [
    { label: 'Usuarios', href: '/system/users' },
    { label: 'Permisos', href: '/system/permissions' },
    { label: 'Auditoria', href: '/system/audit' },
    { label: 'Monitoreo', href: '/system/monitoring' }
  ];
}
