/**
 * Formats a number as currency using Intl.NumberFormat.
 *
 * For template usage, prefer {@link PropertyCurrencyPipe}:
 *   {{ amount | propertyCurrency }}
 *
 * For programmatic usage (e.g. mappers, computed signals):
 *   formatCurrency(1250.5, 'MXN')  // "$1,250.50"
 *
 * @param value       - The numeric amount to format.
 * @param currency    - ISO 4217 currency code. Defaults to 'USD'.
 * @param locale      - BCP 47 locale tag. Defaults to 'es-EC'.
 * @param maxDecimals - Maximum fraction digits. Defaults to 2.
 */
export function formatCurrency(
  value: number,
  currency = 'USD',
  locale = 'es-EC',
  maxDecimals = 2
): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    maximumFractionDigits: maxDecimals,
  }).format(value);
}
