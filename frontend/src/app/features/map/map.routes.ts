import { Routes } from '@angular/router';

export const MAP_ROUTES: Routes = [
  {
    path: '',
    redirectTo: 'map',
    pathMatch: 'full',
  },
  {
    path: 'map',
    loadComponent: () =>
      import('./pages/world-map-page/world-map-page').then((m) => m.WorldMapPageComponent),
  },
  {
    path: 'destinations',
    loadComponent: () =>
      import('./pages/destinations-list-page/destinations-list-page').then(
        (m) => m.DestinationsListPageComponent
      ),
  },
  {
    path: 'destinations/:id',
    loadComponent: () =>
      import('./pages/destination-editor-page/destination-editor-page').then(
        (m) => m.DestinationEditorPageComponent
      ),
  },
];
