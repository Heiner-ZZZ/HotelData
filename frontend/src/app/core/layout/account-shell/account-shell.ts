import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { TopNavComponent } from '../../../shared/ui/top-nav/top-nav';
import { ScrollToTopComponent } from '../../../shared/ui/scroll-to-top/scroll-to-top';

@Component({
  selector: 'app-account-shell',
  imports: [TopNavComponent, RouterOutlet, ScrollToTopComponent],
  templateUrl: './account-shell.html',
  styleUrl: './account-shell.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AccountShellComponent {}
