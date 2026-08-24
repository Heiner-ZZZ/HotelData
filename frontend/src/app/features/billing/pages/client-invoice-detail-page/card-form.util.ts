/**
 * Utilidades puras del formulario de tarjeta del pago en línea (facturas del
 * huésped). Separadas del componente para poder testearlas sin DOM.
 */

/** Deja solo dígitos y limita a 16 (código IIN + cuenta). */
export function normalizeCardNumber(value: string): string {
  return (value || '').replace(/\D/g, '').slice(0, 16);
}

/** Agrupa el número en bloques de 4 (4242 4242 4242 4242). */
export function formatCardNumber(value: string): string {
  return normalizeCardNumber(value).replace(/(.{4})/g, '$1 ').trim();
}

/** Algoritmo de Luhn sobre los dígitos. */
export function luhnCheck(digits: string): boolean {
  const normalized = normalizeCardNumber(digits);
  if (normalized.length !== 16) return false;
  let sum = 0;
  let double = false;
  for (let i = normalized.length - 1; i >= 0; i--) {
    let d = Number(normalized[i]);
    if (double) {
      d *= 2;
      if (d > 9) d -= 9;
    }
    sum += d;
    double = !double;
  }
  return sum % 10 === 0;
}

/** Máscara de presentación: muestra solo los últimos 4 dígitos. */
export function maskCardNumber(value: string): string {
  const last4 = normalizeCardNumber(value).slice(-4);
  if (!last4) return '';
  return `•••• ${last4}`;
}

/**
 * Máscara de display del campo de número (al salir del foco): conserva los
 * primeros y últimos 4 dígitos y oculta el centro — p.ej. `5003 **** **** 7003`.
 * Solo enmascara números completos (16 dígitos); un número a medias se
 * muestra formateado para seguir editándolo.
 */
export function maskCardNumberDisplay(value: string): string {
  const digits = normalizeCardNumber(value);
  if (digits.length !== 16) return formatCardNumber(digits);
  return `${digits.slice(0, 4)} **** **** ${digits.slice(-4)}`;
}

/** Normaliza MM/AA → valida mes 01-12 y fecha no vencida (fin de mes). */
export function isExpiryValid(value: string, now: Date = new Date()): boolean {
  const match = /^(\d{2})\s*\/\s*(\d{2})$/.exec((value || '').trim());
  if (!match) return false;
  const month = Number(match[1]);
  const year = 2000 + Number(match[2]);
  if (month < 1 || month > 12) return false;
  const endOfMonth = new Date(year, month, 0, 23, 59, 59, 999);
  return endOfMonth.getTime() >= now.getTime();
}

/** CVV de 3 o 4 dígitos. */
export function isCvvValid(value: string): boolean {
  return /^\d{3,4}$/.test((value || '').trim());
}

/** Titular no vacío (mínimo 3 caracteres). */
export function isCardHolderValid(value: string): boolean {
  return (value || '').trim().length >= 3;
}
