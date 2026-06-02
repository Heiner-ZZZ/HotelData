import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AccessNavComponent } from '../../../shared/ui/access-nav/access-nav';

@Component({
  selector: 'app-system-admin-shell',
  imports: [AccessNavComponent, RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './system-admin-shell.html',
  styleUrl: './system-admin-shell.scss'
})
export class SystemAdminShellComponent {
  readonly navigation = [
    { label: 'Usuarios', href: '/system/users', icon: 'people' },
    { label: 'Permisos', href: '/system/permissions', icon: 'verified_user' },
    { label: 'Auditoria', href: '/system/audit', icon: 'history' },
    { label: 'Monitoreo', href: '/system/monitoring', icon: 'monitoring' }
  ];
}
