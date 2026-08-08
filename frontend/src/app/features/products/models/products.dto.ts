/**
 * DTOs for the products feature (Fase 4 UI).
 * Maps to backend `hotel_products` collection + restock endpoint.
 */

export interface HotelProductDto {
  product_id: string;
  prop_id: number;
  name: string;
  description: string;
  unit_price: number;
  quantity_available: number;
  category: string;
  type?: 'retail' | 'supply' | 'asset';
  cost_price?: number;
  default_supplier?: string | null;
  supplier_sku?: string | null;
  par_level?: number | null;
  last_purchase_invoice_ref?: string | null;
  /** Resolved expense invoice (server-enriched) — null for legacy refs. */
  last_purchase_invoice?: {
    id: string;
    vendor_name: string;
    invoice_date: string;
    due_date: string;
    total: number;
    status: string;
  } | null;
  last_purchase_qty?: number | null;
  last_purchase_at?: string | null;
  is_active: boolean;
  archived_at?: string | null;
  archived_by?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface HotelProductListDto {
  items: HotelProductDto[];
}

export interface BookingLineItemDto {
  item_id: string;
  product_id: string;
  name: string;
  quantity: number;
  unit_price: number;
  total: number;
  added_at: string;
  added_by: string;
}

export interface BookingLineItemListDto {
  items: BookingLineItemDto[];
}

export interface AddLineItemPayload {
  product_id: string;
  name: string;
  unit_price: number;
  quantity: number;
}

export interface RemoveLineItemResponse {
  ok: boolean;
}

export interface CreateHotelProductPayload {
  name: string;
  description: string;
  category: string;
  type: 'retail' | 'supply' | 'asset';
  cost_price: number;
  unit_price: number;
  quantity_available: number;
  default_supplier?: string | null;
  supplier_sku?: string | null;
  par_level?: number | null;
  is_active: boolean;
}

export interface UpdateHotelProductPayload {
  name?: string;
  description?: string;
  category?: string;
  type?: 'retail' | 'supply' | 'asset';
  cost_price?: number;
  unit_price?: number;
  quantity_available?: number;
  default_supplier?: string | null;
  supplier_sku?: string | null;
  par_level?: number | null;
  is_active?: boolean;
}

export interface RestockPayload {
  qty: number;
  unit_cost: number;
  supplier_name?: string;
  /** Real FK: expense invoice ObjectId — preferred over the legacy free text. */
  invoice_id?: string;
  /** Legacy free-text reference (backend keeps supporting direct API callers). */
  invoice_ref?: string;
}

export interface RestockResponse {
  product_id: string;
  prop_id: number;
  quantity_available: number;
  cost_price: number;
  default_supplier: string;
  last_purchase_invoice_ref: string | null;
  last_purchase_at: string;
  last_purchase_qty: number;
  total_cost: number;
  ledger_journal_id: string;
  updated_at: string;
  updated_by: string;
}