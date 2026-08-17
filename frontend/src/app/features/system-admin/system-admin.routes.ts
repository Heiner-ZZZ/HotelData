import { Routes } from '@angular/router';

import { roleGuard } from '../../core/auth/auth.guard';
import { AuditPageComponent } from './pages/audit-page/audit-page';
import { MonitoringPageComponent } from './pages/monitoring-page/monitoring-page';
import { MonitoringSelectorComponent } from './pages/monitoring-selector/monitoring-selector';
import { MonitoringM2cPageComponent } from './pages/monitoring-m2c-page/monitoring-m2c-page';
import { NotificationsPageComponent } from './pages/notifications-page/notifications-page';
import { SystemPermissionsPageComponent } from './pages/system-permissions-page/system-permissions-page';
import { PERMISSIONS_INTERNAL_ROUTES } from './pages/system-permissions-page/permissions-routes';
import { SystemUsersPageComponent } from './pages/system-users-page/system-users-page';
import { CurrenciesPageComponent } from './pages/currencies-page/currencies-page';

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
    data: { requiredPermission: 'users.read', allowedRoles: ['super_admin', 'admin_sistema'] }
  },
  {
    path: 'permissions',
    component: SystemPermissionsPageComponent,
    canActivate: [roleGuard],
    data: { requiredPermission: 'roles.read', allowedRoles: ['super_admin', 'admin_sistema'] },
    children: PERMISSIONS_INTERNAL_ROUTES,
  },
  {
    path: 'audit',
    component: AuditPageComponent,
    canActivate: [roleGuard],
    data: { requiredPermission: 'audit.read', allowedRoles: ['super_admin', 'admin_sistema', 'auditor_datos', 'operador_datos'] }
  },
  {
    path: 'monitoring',
    component: MonitoringSelectorComponent,
    canActivate: [roleGuard],
    data: { requiredPermission: 'monitoring.read', allowedRoles: ['super_admin', 'admin_sistema', 'auditor_datos', 'operador_datos'] }
  },
  {
    path: 'monitoring/pocketbase_to_mongo',
    component: MonitoringPageComponent,
    canActivate: [roleGuard],
    data: { requiredPermission: 'monitoring.read', allowedRoles: ['super_admin', 'admin_sistema', 'auditor_datos', 'operador_datos'] }
  },
  {
    path: 'monitoring/mongo_to_clickhouse',
    component: MonitoringM2cPageComponent,
    canActivate: [roleGuard],
    data: { requiredPermission: 'monitoring.read', allowedRoles: ['super_admin', 'admin_sistema', 'auditor_datos', 'operador_datos'] }
  },
  {
    path: 'notifications',
    component: NotificationsPageComponent,
    canActivate: [roleGuard],
    data: { requiredPermission: 'monitoring.read', allowedRoles: ['super_admin', 'admin_sistema', 'auditor_datos', 'operador_datos'] }
  },
  {
    path: 'currencies',
    component: CurrenciesPageComponent,
    canActivate: [roleGuard],
    data: { requiredPermission: 'settings.read', allowedRoles: ['super_admin', 'admin_sistema'] }
  }
];
