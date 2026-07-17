import { Routes } from '@angular/router';

import { roleGuard } from '../../core/auth/auth.guard';
import { AuditPageComponent } from './pages/audit-page/audit-page';
import { MonitoringPageComponent } from './pages/monitoring-page/monitoring-page';
import { NotificationsPageComponent } from './pages/notifications-page/notifications-page';
import { SystemPermissionsPageComponent } from './pages/system-permissions-page/system-permissions-page';
import { SystemUsersPageComponent } from './pages/system-users-page/system-users-page';
import { CurrenciesPageComponent } from './pages/currencies-page/currencies-page';
import { BscPageComponent } from '../admin/pages/bsc-page/bsc-page';

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
  },
  {
    path: 'notifications',
    component: NotificationsPageComponent,
    canActivate: [roleGuard],
    data: { allowedRoles: ['super_admin', 'admin_sistema', 'auditor_datos', 'operador_datos'] }
  },
  {
    path: 'currencies',
    component: CurrenciesPageComponent,
    canActivate: [roleGuard],
    data: { allowedRoles: ['super_admin', 'admin_sistema'] }
  },
  {
    path: 'bsc',
    component: BscPageComponent,
    canActivate: [roleGuard],
    data: { allowedRoles: ['super_admin', 'admin_sistema', 'auditor_datos', 'operador_datos'] }
  }
];
