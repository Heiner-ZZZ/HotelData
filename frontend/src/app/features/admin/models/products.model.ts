export interface HotelProduct {
  productId: string;
  propId: number;
  name: string;
  description: string;
  unitPrice: number;
  quantityAvailable: number;
  category: string;
  isActive: boolean;
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
