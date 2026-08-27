import { PROPERTY_TYPES, propertyTypeLabel } from './registration-status.model';

/**
 * El catálogo de tipos de propiedad del dueño (mismo que el wizard de
 * onboarding) solo expone tipos que operan como un hotel (2026-08): se
 * retiraron apartamento y cabaña, que no comparten recepción/housekeeping/
 * estancias cortas. Los labels legados se conservan para que los registros
 * previos sigan mostrando su tipo con nombre (no el valor crudo).
 */
describe('registration-status.model — catálogo de tipos de propiedad (hotel-like)', () => {
  it('solo expone tipos que operan como un hotel', () => {
    expect(PROPERTY_TYPES.map((t) => t.value)).toEqual([
      'hotel',
      'hostal',
      'bed_breakfast',
      'resort',
      'boutique',
    ]);
  });

  it('conserva labels legados para los tipos retirados (visualización de registros previos)', () => {
    expect(propertyTypeLabel('apartamento')).toBe('Apartamento');
    expect(propertyTypeLabel('cabaña')).toBe('Cabaña');
  });

  it('resuelve labels del catálogo vigente', () => {
    expect(propertyTypeLabel('hotel')).toBe('Hotel');
    expect(propertyTypeLabel('boutique')).toBe('Boutique');
    expect(propertyTypeLabel('desconocido')).toBe('desconocido');
  });
});
