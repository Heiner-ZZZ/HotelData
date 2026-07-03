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
    path: 'portal/:employeeId',
    loadComponent: () =>
      import('./pages/employee-dashboard-page/employee-dashboard-page').then(m => m.EmployeeDashboardPageComponent),
  },
  {
    path: ':employeeId',
    loadComponent: () =>
      import('./pages/employee-detail-page/employee-detail-page').then(m => m.EmployeeDetailPageComponent),
  },
];
