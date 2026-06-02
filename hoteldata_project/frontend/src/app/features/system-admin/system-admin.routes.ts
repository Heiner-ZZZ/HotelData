import { Routes } from '@angular/router';

import { AuditPageComponent } from './pages/audit-page/audit-page';
import { MonitoringPageComponent } from './pages/monitoring-page/monitoring-page';
import { SystemPermissionsPageComponent } from './pages/system-permissions-page/system-permissions-page';
import { SystemUsersPageComponent } from './pages/system-users-page/system-users-page';

export const SYSTEM_ADMIN_ROUTES: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'users'
  },
  {
    path: 'users',
    component: SystemUsersPageComponent
  },
  {
    path: 'permissions',
    component: SystemPermissionsPageComponent
  },
  {
    path: 'audit',
    component: AuditPageComponent
  },
  {
    path: 'monitoring',
    component: MonitoringPageComponent
  }
];
