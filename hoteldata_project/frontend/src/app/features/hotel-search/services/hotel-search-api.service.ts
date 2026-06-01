import { inject, Injectable } from '@angular/core';
import { of } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class HotelSearchApiService {
  getSearchPreview() {
    return of([]);
  }
}
