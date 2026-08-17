import { Routes } from '@angular/router';

export const HR_ROUTES: Routes = [
  {
    path: '',
    redirectTo: 'directory',
    pathMatch: 'full',
  },
  {
    path: 'directory',
    loadComponent: () =>
      import('./pages/employee-list-page/employee-list-page').then(m => m.EmployeeListPageComponent),
  },
  {
    path: 'onboarding',
    loadComponent: () =>
      import('./pages/employee-onboarding-page/employee-onboarding-page').then(m => m.EmployeeOnboardingPageComponent),
  },
  {
    path: 'my-portal',
    loadComponent: () =>
      import('./pages/my-portal-redirect/my-portal-redirect').then(m => m.MyPortalRedirectComponent),
  },
  {
    path: 'portal/:employeeId',
    loadComponent: () =>
      import('./pages/employee-dashboard-page/employee-dashboard-page').then(m => m.EmployeeDashboardPageComponent),
  },
  {
    path: 'portal/:employeeId/attendance',
    loadComponent: () =>
      import('./pages/attendance-history-page/attendance-history-page').then(m => m.AttendanceHistoryPageComponent),
  },
  {
    path: 'shifts',
    loadComponent: () =>
      import('./pages/shift-schedule-page/shift-schedule-page').then(m => m.ShiftSchedulePageComponent),
  },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./pages/hr-dashboard-page/hr-dashboard-page').then(m => m.HrDashboardPageComponent),
  },
  {
    path: ':employeeId',
    loadComponent: () =>
      import('./pages/employee-detail-page/employee-detail-page').then(m => m.EmployeeDetailPageComponent),
  },
];
