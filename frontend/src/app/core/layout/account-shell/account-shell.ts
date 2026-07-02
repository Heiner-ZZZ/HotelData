import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { TopNavComponent } from '../../../shared/ui/top-nav/top-nav';
import { NotificationBellComponent } from '../../../features/notifications/components/notification-bell/notification-bell';

@Component({
  selector: 'app-account-shell',
  imports: [TopNavComponent, NotificationBellComponent, RouterOutlet],
  templateUrl: './account-shell.html',
  styleUrl: './account-shell.scss'
})
export class AccountShellComponent {}
