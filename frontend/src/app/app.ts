import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { ToastContainerComponent } from './shared/ui/toast/toast';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, ToastContainerComponent],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {}
