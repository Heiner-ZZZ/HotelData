import { Routes } from '@angular/router';

export const PROPERTIES_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/properties-list-page/properties-list-page').then((m) => m.PropertiesListPageComponent)
  },
  {
    path: ':propertyId/history',
    loadComponent: () =>
      import('./pages/property-history-page/property-history-page').then((m) => m.PropertyHistoryPageComponent)
  },
  {
    path: ':propertyId/edit',
    loadComponent: () =>
      import('./pages/property-edit-page/property-edit-page').then((m) => m.PropertyEditPageComponent),
    data: { operationMode: 'update', operationDetail: 'Perfil del hotel' }
  },
  {
    path: ':propertyId',
    loadComponent: () =>
      import('./pages/property-detail-page/property-detail-page').then((m) => m.PropertyDetailPageComponent)
  }
];
