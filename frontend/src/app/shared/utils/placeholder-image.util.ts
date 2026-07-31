/**
 * Deterministic placeholder image URLs for hotel cards / galleries / modals
 * when the backend hasn't supplied a real photo.
 *
 * Uses loremflickr.com with a `?lock=` param so the same hotel always
 * resolves to the same photo across renders. The single `hotel` tag keeps
 * the URL deterministic without needing per-variant tag fan-out — variant
 * differentiation (lobby / pool / room) is encoded in the `seed` itself,
 * since callers concat a variant suffix (`${id}1`, `${id}2`, …) before
 * passing it in.
 *
 * Hybrid display strategy: `hotel-detail.mapper` composes
 * `[...locals, ...3 fallbacks]` so loremflickr photos serve as visual
 * decorators even when the hotel has its own images configured.
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
  const safeSeed = encodeURIComponent(String(seed ?? 'hotel'));
  return `https://loremflickr.com/${width}/${height}/hotel?lock=${safeSeed}`;
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
