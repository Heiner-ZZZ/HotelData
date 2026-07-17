export interface CurrencyDto {
  code: string;
  name: string;
  symbol: string;
  decimals: number;
  active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface CurrencyListDto {
  currencies: CurrencyDto[];
}
