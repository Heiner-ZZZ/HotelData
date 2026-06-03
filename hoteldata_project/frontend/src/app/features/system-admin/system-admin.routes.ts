import { Routes } from '@angular/router';

import { roleGuard } from '../../core/auth/auth.guard';
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
    component: SystemUsersPageComponent,
    canActivate: [roleGuard],
    data: { allowedRoles: ['super_admin', 'admin_sistema'] }
  },
  {
    path: 'permissions',
    component: SystemPermissionsPageComponent,
    canActivate: [roleGuard],
    data: { allowedRoles: ['super_admin', 'admin_sistema'] }
  },
  {
    path: 'audit',
    component: AuditPageComponent,
    canActivate: [roleGuard],
    data: { allowedRoles: ['super_admin', 'admin_sistema', 'auditor_datos', 'operador_datos'] }
  },
  {
    path: 'monitoring',
    component: MonitoringPageComponent,
    canActivate: [roleGuard],
    data: { allowedRoles: ['super_admin', 'admin_sistema', 'auditor_datos', 'operador_datos'] }
  }
];
