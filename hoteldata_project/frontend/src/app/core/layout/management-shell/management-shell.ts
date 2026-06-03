import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { ManagementTopNavComponent } from '../../../shared/ui/management-top-nav/management-top-nav';
import { SidebarNavComponent } from '../../../shared/ui/sidebar-nav/sidebar-nav';

@Component({
  selector: 'app-management-shell',
  imports: [ManagementTopNavComponent, SidebarNavComponent, RouterOutlet],
  templateUrl: './management-shell.html',
  styleUrl: './management-shell.scss'
})
export class ManagementShellComponent {}
