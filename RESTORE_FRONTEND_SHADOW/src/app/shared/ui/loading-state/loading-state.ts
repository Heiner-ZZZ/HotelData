import { Component, input } from '@angular/core';

@Component({
  selector: 'app-loading-state',
  standalone: true,
  templateUrl: './loading-state.html',
  styleUrl: './loading-state.scss'
})
export class LoadingStateComponent {
  readonly label = input('Cargando informacion...');
}
