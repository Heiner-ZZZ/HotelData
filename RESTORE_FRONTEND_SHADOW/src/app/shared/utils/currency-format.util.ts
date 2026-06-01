export function formatCurrency(
  value: number,
  currency = 'USD',
  locale = 'es-EC'
): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    maximumFractionDigits: 2
  }).format(value);
}
