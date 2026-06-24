import { Routes } from '@angular/router';

export const HOTEL_DETAIL_ROUTES: Routes = [
  {
    path: 'partner-1',
    redirectTo: '/hotels/1'
  },
  {
    path: ':hotelId',
    loadComponent: () =>
      import('./pages/hotel-detail-page/hotel-detail-page').then((m) => m.HotelDetailPageComponent)
  }
];
