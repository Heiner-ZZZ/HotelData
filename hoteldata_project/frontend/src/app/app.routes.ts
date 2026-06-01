import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'search'
  },
  {
    path: '',
    loadComponent: () =>
      import('./core/layout/public-shell/public-shell').then((m) => m.PublicShellComponent),
    children: [
      {
        path: 'search',
        loadChildren: () =>
          import('./features/hotel-search/hotel-search.routes').then((m) => m.HOTEL_SEARCH_ROUTES)
      },
      {
        path: 'hotels',
        loadChildren: () =>
          import('./features/hotel-detail/hotel-detail.routes').then((m) => m.HOTEL_DETAIL_ROUTES)
      },
      {
        path: 'reservations',
        loadChildren: () =>
          import('./features/reservations/reservations.routes').then((m) => m.RESERVATIONS_ROUTES)
      }
    ]
  },
  {
    path: 'admin',
    loadComponent: () =>
      import('./core/layout/admin-shell/admin-shell').then((m) => m.AdminShellComponent),
    children: [
      {
        path: '',
        loadChildren: () => import('./features/admin/admin.routes').then((m) => m.ADMIN_ROUTES)
      },
      {
        path: 'properties',
        loadChildren: () =>
          import('./features/properties/properties.routes').then((m) => m.PROPERTIES_ROUTES)
      },
      {
        path: 'availability',
        loadChildren: () =>
          import('./features/availability/availability.routes').then((m) => m.AVAILABILITY_ROUTES)
      }
    ]
  },
  {
    path: '**',
    redirectTo: 'search'
  }
];
