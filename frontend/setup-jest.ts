import { setupZoneTestEnv } from 'jest-preset-angular/setup-env/zone';

setupZoneTestEnv();

// maplibre-gl toca APIs de navegador al importar (window.URL.createObjectURL),
// que jsdom no expone → rompía cualquier spec que importara componentes con
// mapa. Se mockea el módulo; la lógica real del mapa no se ejercita en jest.
jest.mock('maplibre-gl', () => ({
  __esModule: true,
  default: {
    Map: class {},
    Marker: class {},
    Popup: class {},
    NavigationControl: class {},
    AttributionControl: class {},
    LngLatBounds: class {
      extend() {
        return this;
      }
    },
  },
}));
