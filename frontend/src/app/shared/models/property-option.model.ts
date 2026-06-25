export interface PropertyOption {
  propId: number;
  label: string;
}

export interface PropertyOptionsPage {
  items: PropertyOption[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
  /** When true, the server returned 401 — user should log in. */
  authRequired?: boolean;
}
