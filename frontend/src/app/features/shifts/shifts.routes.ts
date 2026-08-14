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
  {
    path: 'manager-control',
    loadComponent: () =>
      import('./pages/manager-cash-control-page/manager-cash-control-page').then(m => m.ManagerCashControlPageComponent),
  },
  {
    path: 'open-shifts',
    loadComponent: () =>
      import('./pages/open-shifts-overview-page/open-shifts-overview-page').then(m => m.OpenShiftsOverviewPageComponent),
  },
];
