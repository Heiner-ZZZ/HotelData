import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { AccessNavComponent } from '../../../shared/ui/access-nav/access-nav';

@Component({
  selector: 'app-public-shell',
  imports: [AccessNavComponent, RouterOutlet],
  templateUrl: './public-shell.html',
  styleUrl: './public-shell.scss'
})
export class PublicShellComponent {}
