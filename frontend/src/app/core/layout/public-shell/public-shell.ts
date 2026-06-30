import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { TopNavComponent } from '../../../shared/ui/top-nav/top-nav';

@Component({
  selector: 'app-public-shell',
  imports: [TopNavComponent, RouterOutlet],
  templateUrl: './public-shell.html',
  styleUrl: './public-shell.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PublicShellComponent {}
