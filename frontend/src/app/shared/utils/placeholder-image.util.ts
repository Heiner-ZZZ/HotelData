/**
 * Deterministic placeholder image URLs for hotel cards / galleries / modals
 * when the backend hasn't supplied a real photo.
 *
 * Uses loremflickr.com with a `?lock=` param so the same hotel always
 * resolves to the same photo across renders. ALL loremflickr knowledge
 * (host, tag set, lock scheme) lives in this module — callers never
 * hardcode placeholder URLs.
 *
 * ⚠️ TAG COMPUESTO OBLIGATORIO: loremflickr devuelve HTTP 500 para el tag
 * único `hotel` (https://loremflickr.com/400/250/hotel → 500, verificado
 * 2026-08) y para `hotel,suite` / `hotel,bathroom`. Los tags compuestos
 * usados aquí (room, bedroom, living, interior, lobby) responden 200 y
 * sirven JPEG reales, incluso con `?lock=`. Si algún tag empieza a dar 500,
 * reemplazarlo por otro que responda 200.
 *
 * @param seed Any identifier — hotel id, composite key, or string.
 *             Encoded into the URL so collisions are unlikely.
 * @param width Target width in pixels.
 * @param height Target height in pixels.
 */
export function placeholderImageUrl(
  seed: string | number,
  width = 400,
  height = 250,
): string {
  return loremflickrUrl(seed, 'room', width, height);
}

/** Variantes de habitación (tags que hoy responden 200 en loremflickr). */
const ROOM_TAGS = ['room', 'bedroom', 'living', 'interior', 'lobby'] as const;

/**
 * Placeholder determinista para un tipo de habitación sin foto.
 *
 * Cicla las variantes por `roomIdx` (room → bedroom → living → interior →
 * lobby → …) y fija el `?lock=` al hotel: dos habitaciones del mismo hotel
 * siempre muestran la misma foto; hoteles distintos no colisionan.
 *
 * @param roomKey Hotel id (o clave compuesta) — se combina con `roomIdx`
 *                en el lock para que cada habitación sea estable.
 * @param roomIdx Índice de la habitación en la lista (0-based); determina
 *                la variante de foto.
 * @param width   Target width in pixels.
 * @param height  Target height in pixels.
 */
export function roomPlaceholderUrl(
  roomKey: string | number,
  roomIdx: number,
  width = 400,
  height = 250,
): string {
  const tag = ROOM_TAGS[((roomIdx % ROOM_TAGS.length) + ROOM_TAGS.length) % ROOM_TAGS.length];
  const seed = Number(roomKey) * 100 + roomIdx;
  return loremflickrUrl(seed, tag, width, height);
}

/** Construye la URL loremflickr con tag compuesto `hotel,<tag>` + lock. */
function loremflickrUrl(
  seed: string | number,
  tag: string,
  width: number,
  height: number,
): string {
  const safeSeed = encodeURIComponent(String(seed ?? 'hotel'));
  return `https://loremflickr.com/${width}/${height}/hotel,${tag}?lock=${safeSeed}`;
}

/**
 * Type guard for URLs that are safe to bind to `<img [src]="">`. Returns
 * `true` if `url` is a non-empty, non-whitespace string. Acts as a TS
 * type guard so `arr.filter(isValidImageUrl)` narrows the result to
 * `string[]`.
 *
 * Use this in any `Array.prototype.filter` callback that gates image
 * arrays coming from a backend (rented images, hotel photos,
 * amenity photos, room-type thumbnails). The empty-string case matters
 * because browsers resolve `<img src="">` to the current page URL and
 * never fire `onError`, so the visual fallback (placeholder, icon,
 * or alt text) would never kick in.
 *
 * Whitespace-only strings (e.g. `"   "`) are also rejected — most CDN
 * signed URLs would percent-encode them into garbage on canonicalisation.
 *
 * @param url Any value that may or may not be a valid image URL.
 * @returns true if `url` is a non-empty trimmed string.
 */
export function isValidImageUrl(url: unknown): url is string {
  if (typeof url !== 'string') return false;
  return url.trim().length > 0;
}

/**
 * Single-slot hybrid: returns `realUrl` if it is a non-empty, non-whitespace
 * string; otherwise synthesises a deterministic loremflickr URL from
 * `seed`. Use this for shapes that have exactly ONE image slot (similar
 * hotels card, hotel-detail's `imageUrl`, hotel-compare row), for which
 * the gallery-style `[...N locals, 3 fallbacks]` pattern does not apply.
 *
 * Empty-string safety matters: `<img src="">` resolves to the current
 * page URL in browsers and never fires `onError`, so the visual fallback
 * would never kick in. The `||` operator alone would not catch this case.
 *
 * @param realUrl Backend-supplied URL. May be `null`, `undefined`, `''`,
 *                or a whitespace-only string. All four are treated as
 *                missing and trigger the placeholder.
 * @param seed    Same contract as {@link placeholderImageUrl}.
 * @param width   Target width in pixels.
 * @param height  Target height in pixels.
 */
export function placeholderOrFallback(
  realUrl: string | null | undefined,
  seed: string | number,
  width = 400,
  height = 250,
): string {
  if (isValidImageUrl(realUrl)) {
    return realUrl;
  }
  return placeholderImageUrl(seed, width, height);
}

/**
 * Galería centralizada para cards de hotel — usada por `/welcome`
 * (featured) y `/search` (hotel-card). Garantiza que el mismo hotel
 * siempre muestre las mismas 3 imágenes placeholder en ambas vistas,
 * sin duplicar la lógica de semillas en cada mapper/componente.
 *
 * Antes cada feature generaba sus placeholders con semillas distintas
 * (`${id}1` vs `${id}-hotel`) y con lógica dispersa; `/welcome` llegó
 * a consultar 3 veces la misma URL (sin variación de lock). Centralizar
 * aquí hace que `/welcome` y `/search` compartan exactamente el mismo
 * `hotel,room?lock=` y que la variación sea determinista.
 *
 * @param propId Hotel id (o clave compuesta) — fija el lock base.
 * @param imageUrl URL real del hotel (si existe) — se antepone sin mutar.
 * @param placeholderCount Cuántos placeholders generar (default 3).
 * @param width Ancho del placeholder.
 * @param height Alto del placeholder.
 * @returns Array con 0..1 URL real + `placeholderCount` URLs loremflickr
 *          distintas (`hotel,room` con locks `${propId}-1`, `${propId}-2`…).
 */
export function hotelGalleryImages(
  propId: number | string,
  imageUrl: string | null | undefined,
  placeholderCount = 3,
  width = 400,
  height = 250,
): string[] {
  const primary = isValidImageUrl(imageUrl) ? [imageUrl as string] : [];
  // Variedad visual real: cada placeholder usa un tag distinto (room→bedroom→living…)
  // igual que `roomPlaceholderUrl`. Con el bug anterior los 3 usaban `hotel,room`
  // con locks distintos pero la misma foto; ahora cada índice cambia de tag y
  // de lock, garantizando 3 fotos distintas y compartidas entre /welcome y /search.
  const placeholders = Array.from({ length: placeholderCount }, (_, i) =>
    roomPlaceholderUrl(propId, i, width, height),
  );
  return [...primary, ...placeholders];
}
