import { Routes } from '@angular/router';

export const HOTEL_DETAIL_ROUTES: Routes = [
  {
    path: ':hotelId',
    loadComponent: () =>
      import('./pages/hotel-detail-page/hotel-detail-page').then((m) => m.HotelDetailPageComponent)
  }
];
