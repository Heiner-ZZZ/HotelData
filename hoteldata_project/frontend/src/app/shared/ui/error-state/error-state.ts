import { Component, input } from '@angular/core';

@Component({
  selector: 'app-error-state',
  templateUrl: './error-state.html',
  styleUrl: './error-state.scss'
})
export class ErrorStateComponent {
  readonly title = input('No fue posible cargar esta seccion');
  readonly description = input('Intenta nuevamente o revisa la conectividad con la API.');
}
