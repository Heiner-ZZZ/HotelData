import { readFileSync } from 'node:fs';

/** Este preset no inyecta estilos en el DOM: el contrato visual se verifica
 *  compilando el SCSS real del partial (mismo patrón que onboarding-property). */
const sass = (tryRequire('sass') ?? tryRequire('sass-embedded')) as {
  compileString: (s: string) => { css: string };
};
function tryRequire(name: string): unknown {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  try { return require(name); } catch { return null; }
}

function compiledCss(): string {
  const scss = readFileSync(`${__dirname}/_hd-bento-gallery.scss`, 'utf-8');
  return sass.compileString(scss).css.replace(/\s+/g, '');
}

/**
 * La galería hero debe enmarcar TODAS las fotos en celdas uniformes, estilo
 * Booking.com/Expedia: un rectángulo definido por aspect-ratio donde cada
 * imagen recorta con object-fit: cover. Sin un marco definido, las filas
 * (grid 1fr) se dimensionan al alto natural de cada foto — y como las fotos
 * reales del dueño tienen tamaño/aspecto arbitrario frente a los placeholders
 * loremflickr 400x250, cada imagen quedaba más chica que la anterior hasta
 * quedar ilegibles las últimas.
 */
describe('_hd-bento-gallery — marco uniforme (Booking.com/Expedia)', () => {
  it('el hero tiene un marco definido por aspect-ratio (celdas uniformes, no al alto natural)', () => {
    const css = compiledCss();
    const base = css.match(/\.bento-gallery\{([^}]*)\}/);
    expect(base).not.toBeNull();
    expect(base![1]).toContain('aspect-ratio:4/3'); // móvil: hero 4:3

    const desktop = css.match(/@media\(min-width:768px\)\{\.bento-gallery\{([^}]*)\}\}/);
    expect(desktop).not.toBeNull();
    expect(desktop![1]).toContain('aspect-ratio:16/9'); // desktop: hero 16:9
  });

  it('las imágenes del hero recortan a la celda con object-fit: cover y llenan el 100%', () => {
    const css = compiledCss();
    expect(css).toMatch(/\.bento-main\s*img\{[^}]*object-fit:cover/);
    expect(css).toMatch(/\.bento-thumb\s*img\{[^}]*object-fit:cover/);
  });

  it('las celdas ocultan el desborde (overflow: hidden) para que el cover no se salga', () => {
    const css = compiledCss();
    expect(css).toMatch(/\.bento-main\{[^}]*overflow:hidden/);
    expect(css).toMatch(/\.bento-thumb\{[^}]*overflow:hidden/);
  });

  it('el placeholder de imagen rota llena la celda (height 100%, no px fijos)', () => {
    const css = compiledCss();
    expect(css).toMatch(/\.img-placeholder-lg\{[^}]*height:100%/);
  });
});
