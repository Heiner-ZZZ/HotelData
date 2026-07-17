export interface Currency {
  code: string;
  name: string;
  symbol: string;
  decimals: number;
  active: boolean;
}

export interface CurrencyListViewModel {
  currencies: Currency[];
}
