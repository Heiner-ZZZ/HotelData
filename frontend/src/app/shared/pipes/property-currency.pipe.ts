import { inject, Pipe, PipeTransform } from '@angular/core';
import { PropertyContextService } from '../services/property-context.service';

/**
 * Pipe that formats a number as currency using the current property's
 * configured currency from PropertyContextService.
 *
 * Usage in templates:
 *   {{ 1250.50 | propertyCurrency }}           // "$1,250.50 USD"  (es-EC locale)
 *   {{ 1250.50 | propertyCurrency:'MXN' }}     // "$1,250.50"       (override currency)
 *   {{ 1250.50 | propertyCurrency:undefined:'en-US' }} // "$1,250.50" (override locale)
 */
@Pipe({
  name: 'propertyCurrency',
  standalone: true,
  pure: false, // Must react to currentCurrency() signal changes even when value argument stays the same
})
export class PropertyCurrencyPipe implements PipeTransform {
  private readonly propertyCtx = inject(PropertyContextService);

  transform(
    value: number | null | undefined,
    currency?: string,
    locale?: string,
    maxDecimals?: number
  ): string {
    if (value == null || isNaN(value)) return '—';

    const cur = currency || this.propertyCtx.currentCurrency() || 'USD';
    const loc = locale || 'es-EC';
    const max = maxDecimals ?? 2;

    return new Intl.NumberFormat(loc, {
      style: 'currency',
      currency: cur,
      maximumFractionDigits: max,
    }).format(value);
  }
}
