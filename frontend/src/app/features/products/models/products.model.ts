/**
 * Domain models for the products feature (Fase 4 UI).
 */

export type ProductType = 'retail' | 'supply' | 'asset';

export const PRODUCT_TYPE_LABELS: Record<ProductType, string> = {
  retail: 'Retail',
  supply: 'Suministro',
  asset: 'Activo',
};

export interface HotelProduct {
  productId: string;
  propId: number;
  name: string;
  description: string;
  category: string;
  type: ProductType;
  costPrice: number;
  unitPrice: number;
  quantityAvailable: number;
  defaultSupplier: string | null;
  supplierSku: string | null;
  parLevel: number | null;
  lastPurchaseInvoiceRef: string | null;
  /** Resolved expense invoice (real FK) — null for legacy free-text refs. */
  lastPurchaseInvoice: LastPurchaseInvoice | null;
  lastPurchaseQty: number | null;
  lastPurchaseAt: string | null;
  isActive: boolean;
  archivedAt: string | null;
  archivedBy: string | null;
  createdAt?: string;
  updatedAt?: string;
}

export interface LastPurchaseInvoice {
  id: string;
  vendorName: string;
  invoiceDate: string;
  dueDate: string;
  total: number;
  status: string;
}

export interface BookingLineItem {
  itemId: string;
  productId: string;
  name: string;
  quantity: number;
  unitPrice: number;
  total: number;
  addedAt: string;
  addedBy: string;
}

export interface RestockResult {
  productId: string;
  propId: number;
  quantityAvailable: number;
  costPrice: number;
  defaultSupplier: string;
  lastPurchaseInvoiceRef: string | null;
  lastPurchaseQty: number;
  totalCost: number;
  ledgerJournalId: string;
  updatedBy: string;
}