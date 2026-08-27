import { readFileSync } from 'node:fs';

import { TestBed } from '@angular/core/testing';

import { LocationPickerComponent, mapTileStyleUrl } from './location-picker';

/**
 * Stubs del engine MapLibre: jsdom no tiene WebGL. El stub de Map registra el
 * handler de 'click' y cuenta resize() para verificar el contrato responsivo
 * del mapa de /alojamiento (mismo proveedor de tiles que compare/competitive).
 * Las clases viven DENTRO de la factory (jest hoistea jest.mock antes de
 * inicializar cualquier variable de módulo); se acceden vía requireMock.
 */
interface MapStub {
  clickHandler: ((e: { lngLat: { lat: number; lng: number } }) => void) | null;
  resizeCount: number;
}
interface MapStubCtor {
  new (): MapStub;
  instances: MapStub[];
}

jest.mock('maplibre-gl', () => {
  class MockMap {
    static instances: MapStub[] = [];
    clickHandler: MapStub['clickHandler'] = null;
    resizeCount = 0;

    constructor() {
      MockMap.instances.push(this);
    }

    addControl = () => undefined;
    on(event: string, handler: unknown) {
      if (event === 'click') this.clickHandler = handler as MapStub['clickHandler'];
    }
    easeTo = () => undefined;
    remove = () => undefined;
    resize() {
      this.resizeCount += 1;
    }
  }

  class MockMarker {
    setLngLat() {
      return this;
    }
    addTo() {
      return this;
    }
    on = () => undefined;
    remove = () => undefined;
    getLngLat() {
      return { lat: 19.4326, lng: -99.1332 };
    }
  }

  return {
    __esModule: true,
    default: {
      Map: MockMap,
      Marker: MockMarker,
      NavigationControl: class {},
      AttributionControl: class {},
    },
  };
});

/** jsdom no implementa ResizeObserver; se mockea como clase observable. */
class ResizeObserverMock implements ResizeObserver {
  static instances: ResizeObserverMock[] = [];
  observed: Element[] = [];
  private readonly callback: ResizeObserverCallback;

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
    ResizeObserverMock.instances.push(this);
  }

  observe(el: Element) {
    this.observed.push(el);
  }
  unobserve = () => undefined;
  disconnect = () => undefined;

  /** Helper de test: dispara el callback con un ancho dado. */
  trigger(width: number): void {
    this.callback(
      [{ contentRect: { width, height: 400 } } as ResizeObserverEntry],
      this as unknown as ResizeObserver,
    );
  }
}

beforeAll(() => {
  globalThis.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver;
});

function maplibreMock() {
  return jest.requireMock('maplibre-gl') as { default: { Map: MapStubCtor } };
}

describe('LocationPickerComponent — mapa responsivo de /alojamiento', () => {
  function setup() {
    ResizeObserverMock.instances = [];
    maplibreMock().default.Map.instances = [];
    TestBed.configureTestingModule({ imports: [LocationPickerComponent] });
    const fixture = TestBed.createComponent(LocationPickerComponent);
    fixture.detectChanges();
    return { fixture, comp: fixture.componentInstance };
  }

  it('usa el proveedor de tiles OpenFreeMap compartido con compare/competitive', () => {
    expect(mapTileStyleUrl()).toBe('https://tiles.openfreemap.org/styles/liberty');
  });

  it('observa el contenedor del mapa para re-encuadrar el canvas al cambiar el tamaño', () => {
    const { comp } = setup();
    const observer = ResizeObserverMock.instances[0];
    expect(observer).toBeTruthy();
    expect(observer.observed).toContain(comp.mapContainer().nativeElement);
  });

  it('llama map.resize() cuando el contenedor crece o se encoge (responsivo)', () => {
    setup();
    const map = maplibreMock().default.Map.instances[0];
    const observer = ResizeObserverMock.instances[0];

    expect(map.resizeCount).toBe(0);
    observer.trigger(800);
    expect(map.resizeCount).toBe(1);
    observer.trigger(420);
    expect(map.resizeCount).toBe(2);
  });

  it('no llama resize() mientras el contenedor está oculto (ancho 0)', () => {
    setup();
    const map = maplibreMock().default.Map.instances[0];
    ResizeObserverMock.instances[0].trigger(0);
    expect(map.resizeCount).toBe(0);
  });

  it('la altura del contenedor es dinámica (clamp en vh), no fija en px', () => {
    setup();
    const source = readFileSync(`${__dirname}/location-picker.ts`, 'utf-8');
    expect(source).toMatch(/\.map-container\s*\{\s*height:\s*clamp\(/);
    expect(source).not.toMatch(/\.map-container\s*\{\s*height:\s*\d+px/);
  });

  it('emite locationChange al hacer clic en el mapa', () => {
    const { comp } = setup();
    let emitted: { latitude: number; longitude: number } | null = null;
    comp.locationChange.subscribe((v) => (emitted = v));

    maplibreMock().default.Map.instances[0].clickHandler?.({
      lngLat: { lat: -0.1807, lng: -78.4678 },
    });

    expect(emitted).toEqual({ latitude: -0.1807, longitude: -78.4678 });
  });
});
