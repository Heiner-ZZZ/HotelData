import { Routes } from '@angular/router';

export const HOTEL_COMPARE_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/hotel-compare-page/hotel-compare-page').then((m) => m.HotelComparePageComponent)
  }
];
