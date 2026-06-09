import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { TopNavComponent } from '../../../shared/ui/top-nav/top-nav';

@Component({
  selector: 'app-account-shell',
  imports: [TopNavComponent, RouterOutlet],
  templateUrl: './account-shell.html',
  styleUrl: './account-shell.scss'
})
export class AccountShellComponent {}
