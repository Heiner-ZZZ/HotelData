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
    path: 'operations',
    loadComponent: () =>
      import('./pages/housekeeping-operations-page/housekeeping-operations-page').then(
        (m) => m.HousekeepingOperationsPageComponent
      ),
  },
  {
    path: 'calendar',
    loadComponent: () =>
      import('./pages/housekeeping-calendar-page/housekeeping-calendar-page').then(
        (m) => m.HousekeepingCalendarPageComponent
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
    path: 'matrix',
    loadComponent: () =>
      import('./pages/room-status-dashboard-page/room-status-dashboard-page').then(
        (m) => m.RoomStatusDashboardPageComponent
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
