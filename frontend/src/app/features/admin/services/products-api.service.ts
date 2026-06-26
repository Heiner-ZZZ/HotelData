import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import type {
  AddLineItemPayload,
  BookingLineItemDto,
  BookingLineItemListDto,
  HotelProductDto,
  HotelProductListDto,
  RemoveLineItemResponse,
} from '../models/products.dto';
import type { BookingLineItem, HotelProduct } from '../models/products.model';

function mapProduct(dto: HotelProductDto): HotelProduct {
  return {
    productId: dto.product_id,
    propId: dto.prop_id,
    name: dto.name,
    description: dto.description ?? '',
    unitPrice: dto.unit_price ?? 0,
    quantityAvailable: dto.quantity_available ?? 0,
    category: dto.category ?? 'Otros',
    isActive: dto.is_active ?? true,
  };
}

function mapLineItem(dto: BookingLineItemDto): BookingLineItem {
  return {
    itemId: dto.item_id,
    productId: dto.product_id,
    name: dto.name,
    quantity: dto.quantity,
    unitPrice: dto.unit_price,
    total: dto.total,
    addedAt: dto.added_at,
    addedBy: dto.added_by,
  };
}

@Injectable({ providedIn: 'root' })
export class ProductsApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly base = `${this.apiConfig.baseUrl}/management/products`;

  /** List all billable products for a hotel */
  listHotelProducts(propId: number): Observable<HotelProduct[]> {
    return this.http
      .get<HotelProductListDto>(`${this.base}/hotels/${propId}`, { withCredentials: true })
      .pipe(map((dto) => (dto.items ?? []).map(mapProduct)));
  }

  /** Get all line items (add-on products) for a booking */
  getLineItems(bookingId: string): Observable<BookingLineItem[]> {
    return this.http
      .get<BookingLineItemListDto>(`${this.base}/bookings/${bookingId}/line-items`, { withCredentials: true })
      .pipe(map((dto) => (dto.items ?? []).map(mapLineItem)));
  }

  /** Add a product as a line item to an active booking */
  addLineItem(bookingId: string, payload: AddLineItemPayload): Observable<BookingLineItem> {
    return this.http
      .post<BookingLineItemDto>(`${this.base}/bookings/${bookingId}/line-items`, payload, { withCredentials: true })
      .pipe(map(mapLineItem));
  }

  /** Remove a line item from a booking */
  removeLineItem(bookingId: string, itemId: string): Observable<boolean> {
    return this.http
      .delete<RemoveLineItemResponse>(`${this.base}/bookings/${bookingId}/line-items/${itemId}`, { withCredentials: true })
      .pipe(map((res) => res.ok));
  }
}
