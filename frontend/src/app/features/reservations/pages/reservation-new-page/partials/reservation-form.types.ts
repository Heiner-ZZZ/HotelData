import type { AbstractControl } from '@angular/forms';

export interface ReservationFormControls {
  propId: AbstractControl;
  guestName: AbstractControl;
  guestEmail: AbstractControl;
  guestPhone: AbstractControl;
  cedula: AbstractControl;
  checkInDate: AbstractControl;
  checkOutDate: AbstractControl;
  checkInTime: AbstractControl;
  checkOutTime: AbstractControl;
  adults: AbstractControl;
  children: AbstractControl;
  rooms: AbstractControl;
  comment: AbstractControl;
  couponCode: AbstractControl;
  specialRequests: AbstractControl;
}

export interface ReservationFormLike {
  controls: ReservationFormControls;
}

export interface RecentGuestView {
  name: string;
  email: string;
  phone: string;
  cedula?: string;
}
