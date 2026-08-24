import {
  formatCardNumber,
  isCardHolderValid,
  isCvvValid,
  isExpiryValid,
  luhnCheck,
  maskCardNumber,
  maskCardNumberDisplay,
  normalizeCardNumber,
} from './card-form.util';

describe('card-form.util — validación del pago en línea', () => {
  it('normalizeCardNumber deja solo dígitos y limita a 16', () => {
    expect(normalizeCardNumber('4242 4242 4242 4242')).toBe('4242424242424242');
    expect(normalizeCardNumber('4111-1111-1111-1111')).toBe('4111111111111111');
    expect(normalizeCardNumber('12345678901234567890')).toBe('1234567890123456');
    expect(normalizeCardNumber('')).toBe('');
  });

  it('formatCardNumber agrupa en bloques de 4', () => {
    expect(formatCardNumber('4242424242424242')).toBe('4242 4242 4242 4242');
    expect(formatCardNumber('4242 4242 4242 4242')).toBe('4242 4242 4242 4242');
  });

  it('luhnCheck acepta números reales de tarjeta y rechaza inválidos', () => {
    expect(luhnCheck('4242424242424242')).toBe(true);
    expect(luhnCheck('4111111111111111')).toBe(true);
    expect(luhnCheck('4242424242424241')).toBe(false);
    expect(luhnCheck('1234567890123456')).toBe(false);
    expect(luhnCheck('4242')).toBe(false);
    expect(luhnCheck('')).toBe(false);
  });

  it('maskCardNumber solo expone los últimos 4 dígitos', () => {
    expect(maskCardNumber('4242424242427812')).toBe('•••• 7812');
    expect(maskCardNumber('4242 4242 4242 7812')).toBe('•••• 7812');
    expect(maskCardNumber('')).toBe('');
  });

  it('maskCardNumberDisplay enmascara el centro al salir del campo (5003 **** **** 7003)', () => {
    expect(maskCardNumberDisplay('5003700370037003')).toBe('5003 **** **** 7003');
    expect(maskCardNumberDisplay('4242 4242 4242 4242')).toBe('4242 **** **** 4242');
  });

  it('maskCardNumberDisplay NO enmascara números incompletos (devuelve el formato editable)', () => {
    expect(maskCardNumberDisplay('5003 7003')).toBe('5003 7003');
    expect(maskCardNumberDisplay('')).toBe('');
    expect(maskCardNumberDisplay('500370037003700')).toBe('5003 7003 7003 700');
  });

  it('isExpiryValid valida formato MM/AA y fecha no vencida', () => {
    const now = new Date(2026, 7, 23); // 23 ago 2026
    expect(isExpiryValid('12/30', now)).toBe(true);
    expect(isExpiryValid('08/26', now)).toBe(true); // fin de mes de agosto 2026
    expect(isExpiryValid('07/26', now)).toBe(false); // julio ya venció
    expect(isExpiryValid('13/30', now)).toBe(false); // mes inválido
    expect(isExpiryValid('00/30', now)).toBe(false);
    expect(isExpiryValid('12/30', now)).toBe(true);
    expect(isExpiryValid('', now)).toBe(false);
    expect(isExpiryValid('1230', now)).toBe(false); // sin separador
  });

  it('isCvvValid acepta 3-4 dígitos', () => {
    expect(isCvvValid('123')).toBe(true);
    expect(isCvvValid('1234')).toBe(true);
    expect(isCvvValid('12')).toBe(false);
    expect(isCvvValid('12345')).toBe(false);
    expect(isCvvValid('12a')).toBe(false);
    expect(isCvvValid('')).toBe(false);
  });

  it('isCardHolderValid exige un titular no vacío', () => {
    expect(isCardHolderValid('ANA GARCIA')).toBe(true);
    expect(isCardHolderValid('Ana')).toBe(true);
    expect(isCardHolderValid('')).toBe(false);
    expect(isCardHolderValid('  ')).toBe(false);
  });
});
