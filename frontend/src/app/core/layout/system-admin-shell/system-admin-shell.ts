import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { ManagementTopNavComponent } from '../../../shared/ui/management-top-nav/management-top-nav';
import { ScrollToTopComponent } from '../../../shared/ui/scroll-to-top/scroll-to-top';
import { SidebarNavComponent } from '../../../shared/ui/sidebar-nav/sidebar-nav';

@Component({
  selector: 'app-system-admin-shell',
  imports: [ManagementTopNavComponent, ScrollToTopComponent, SidebarNavComponent, RouterOutlet],
  templateUrl: './system-admin-shell.html',
  styleUrl: './system-admin-shell.scss'
})
export class SystemAdminShellComponent {}
