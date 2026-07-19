import { Routes } from '@angular/router';

export const HOTEL_SEARCH_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/hotel-search-page/hotel-search-page').then((m) => m.HotelSearchPageComponent)
  },
  {
    path: 'favorites',
    loadComponent: () =>
      import('./pages/favorites-page/favorites-page').then((m) => m.FavoritesPageComponent)
  }
];
