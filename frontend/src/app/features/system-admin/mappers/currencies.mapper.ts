import type { CurrencyDto } from '../models/currencies.dto';
import type { Currency } from '../models/currencies.model';

export function mapCurrency(dto: CurrencyDto): Currency {
  return {
    code: dto.code,
    name: dto.name,
    symbol: dto.symbol,
    decimals: dto.decimals,
    active: dto.active,
  };
}
