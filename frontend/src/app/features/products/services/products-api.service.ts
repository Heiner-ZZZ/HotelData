import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import type {
  AddLineItemPayload,
  BookingLineItemDto,
  BookingLineItemListDto,
  CreateHotelProductPayload,
  HotelProductDto,
  HotelProductListDto,
  RemoveLineItemResponse,
  RestockPayload,
  RestockResponse,
  UpdateHotelProductPayload,
} from '../models/products.dto';
import type {
  BookingLineItem,
  HotelProduct,
  ProductType,
  RestockResult,
} from '../models/products.model';

export function mapProduct(dto: HotelProductDto): HotelProduct {
  return {
    productId: dto.product_id,
    propId: dto.prop_id,
    name: dto.name,
    description: dto.description ?? '',
    category: dto.category ?? 'Otros',
    type: (dto.type ?? 'retail') as ProductType,
    costPrice: dto.cost_price ?? 0,
    unitPrice: dto.unit_price ?? 0,
    quantityAvailable: dto.quantity_available ?? 0,
    defaultSupplier: dto.default_supplier ?? null,
    supplierSku: dto.supplier_sku ?? null,
    parLevel: dto.par_level ?? null,
    lastPurchaseInvoiceRef: dto.last_purchase_invoice_ref ?? null,
    lastPurchaseInvoice: dto.last_purchase_invoice
      ? {
          id: dto.last_purchase_invoice.id,
          vendorName: dto.last_purchase_invoice.vendor_name,
          invoiceDate: dto.last_purchase_invoice.invoice_date,
          dueDate: dto.last_purchase_invoice.due_date,
          total: dto.last_purchase_invoice.total,
          status: dto.last_purchase_invoice.status,
        }
      : null,
    lastPurchaseQty: dto.last_purchase_qty ?? null,
    lastPurchaseAt: dto.last_purchase_at ?? null,
    isActive: dto.is_active ?? true,
    archivedAt: dto.archived_at ?? null,
    archivedBy: dto.archived_by ?? null,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
  };
}

export function mapLineItem(dto: BookingLineItemDto): BookingLineItem {
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

export function mapRestock(dto: RestockResponse): RestockResult {
  return {
    productId: dto.product_id,
    propId: dto.prop_id,
    quantityAvailable: dto.quantity_available,
    costPrice: dto.cost_price,
    defaultSupplier: dto.default_supplier,
    lastPurchaseInvoiceRef: dto.last_purchase_invoice_ref,
    lastPurchaseQty: dto.last_purchase_qty,
    totalCost: dto.total_cost,
    ledgerJournalId: dto.ledger_journal_id,
    updatedBy: dto.updated_by,
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

  /** Create a new hotel product */
  createHotelProduct(propId: number, payload: CreateHotelProductPayload): Observable<HotelProduct> {
    return this.http
      .post<HotelProductDto>(`${this.base}/hotels/${propId}`, payload, { withCredentials: true })
      .pipe(map(mapProduct));
  }

  /** Update an existing hotel product */
  updateHotelProduct(propId: number, productId: string, payload: UpdateHotelProductPayload): Observable<HotelProduct> {
    return this.http
      .put<HotelProductDto>(`${this.base}/hotels/${propId}/${productId}`, payload, { withCredentials: true })
      .pipe(map(mapProduct));
  }

  /** Soft-delete (deactivate) a hotel product */
  deleteHotelProduct(propId: number, productId: string): Observable<{ ok: boolean }> {
    return this.http
      .delete<{ ok: boolean }>(`${this.base}/hotels/${propId}/${productId}`, { withCredentials: true });
  }

  /** Restock: increment quantity_available + update cost_price + post DR 1050 / CR 2010 */
  restockProduct(propId: number, productId: string, payload: RestockPayload): Observable<RestockResult> {
    return this.http
      .post<RestockResponse>(`${this.base}/hotels/${propId}/${productId}/restock`, payload, { withCredentials: true })
      .pipe(map(mapRestock));
  }

  /** Get all line items (add-on products) for a booking. Migración E: prop_id
 *  en query (gate por-hotel + pertenencia del booking al hotel). */
  getLineItems(bookingId: string, propId: number): Observable<BookingLineItem[]> {
    return this.http
      .get<BookingLineItemListDto>(`${this.base}/bookings/${bookingId}/line-items`, {
        params: { prop_id: String(propId) },
        withCredentials: true,
      })
      .pipe(map((dto) => (dto.items ?? []).map(mapLineItem)));
  }

  /** Add a product as a line item to an active booking. */
  addLineItem(bookingId: string, payload: AddLineItemPayload, propId: number): Observable<BookingLineItem> {
    return this.http
      .post<BookingLineItemDto>(`${this.base}/bookings/${bookingId}/line-items`, payload, {
        params: { prop_id: String(propId) },
        withCredentials: true,
      })
      .pipe(map(mapLineItem));
  }

  /** Remove a line item from a booking. */
  removeLineItem(bookingId: string, itemId: string, propId: number): Observable<boolean> {
    return this.http
      .delete<RemoveLineItemResponse>(`${this.base}/bookings/${bookingId}/line-items/${itemId}`, {
        params: { prop_id: String(propId) },
        withCredentials: true,
      })
      .pipe(map((res) => res.ok));
  }
}