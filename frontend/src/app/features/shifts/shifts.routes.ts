import { Routes } from '@angular/router';

export const SHIFTS_ROUTES: Routes = [
  {
    path: '',
    redirectTo: 'dashboard',
    pathMatch: 'full',
  },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./pages/control-turnos-caja-page/control-turnos-caja-page').then(m => m.ControlTurnosCajaPageComponent),
  },
];
