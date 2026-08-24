import { tileLayerConfig } from './competitive-map';

describe('CompetitiveMapComponent — proveedor de tiles (render fiable)', () => {
  it('usa OpenFreeMap (el mismo proveedor que ya renderiza en hotels/compare)', () => {
    const cfg = tileLayerConfig();
    expect(cfg.styleUrl).toContain('tiles.openfreemap.org');
    expect(cfg.styleUrl).toContain('styles/liberty');
  });

  it('NO usa el OSM público ni CartoDB (no cargaban en la red del cliente)', () => {
    const cfg = tileLayerConfig();
    expect(cfg.styleUrl).not.toContain('openstreetmap.org');
    expect(cfg.styleUrl).not.toContain('cartocdn.com');
  });

  it('expone la atribución de OpenMapTiles / OpenStreetMap', () => {
    expect(tileLayerConfig().attribution).toMatch(/OpenMapTiles|OpenStreetMap/);
  });
});
