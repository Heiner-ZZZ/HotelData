import { Routes } from '@angular/router';

export const HOUSEKEEPING_ROUTES: Routes = [
  {
    path: '',
    redirectTo: 'dashboard',
    pathMatch: 'full',
  },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./pages/housekeeping-dashboard-page/housekeeping-dashboard-page').then(
        (m) => m.HousekeepingDashboardPageComponent
      ),
  },
  {
    path: 'rooms',
    loadComponent: () =>
      import('./pages/room-status-page/room-status-page').then(
        (m) => m.RoomStatusPageComponent
      ),
  },
  {
    path: 'tasks',
    loadComponent: () =>
      import('./pages/housekeeping-tasks-page/housekeeping-tasks-page').then(
        (m) => m.HousekeepingTasksPageComponent
      ),
  },
  {
    path: 'maintenance',
    loadComponent: () =>
      import('./pages/maintenance-page/maintenance-page').then(
        (m) => m.MaintenancePageComponent
      ),
  },
  {
    path: 'charges',
    loadComponent: () =>
      import('./pages/additional-charges-page/additional-charges-page').then(
        (m) => m.AdditionalChargesPageComponent
      ),
  },
  {
    path: 'history',
    loadComponent: () =>
      import('./pages/room-history-page/room-history-page').then(
        (m) => m.RoomHistoryPageComponent
      ),
  },
];
