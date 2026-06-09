export interface ApiError {
  status: number;
  message: string;
  code?: string;
  details?: unknown;
}
