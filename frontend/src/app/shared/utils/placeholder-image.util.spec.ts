import {
  hotelGalleryImages,
  placeholderImageUrl,
  placeholderOrFallback,
  roomPlaceholderUrl,
} from './placeholder-image.util';

describe('placeholderImageUrl — fotos loremflickr deterministas', () => {
  it('genera una URL loremflickr con tag compuesto (el tag único "hotel" devuelve 500)', () => {
    const url = placeholderImageUrl(7);
    expect(url.startsWith('https://loremflickr.com/')).toBe(true);
    expect(url).toContain('/hotel,room?lock=');
    expect(url).not.toContain('/hotel?lock=');
  });

  it('es determinista: el mismo seed produce la misma URL', () => {
    expect(placeholderImageUrl('hotel-1')).toBe(placeholderImageUrl('hotel-1'));
  });

  it('respeta el ancho y alto pedidos', () => {
    expect(placeholderImageUrl('x', 800, 400)).toContain('/800/400/');
  });

  it('semillas distintas dan URLs distintas (variedad por hotel)', () => {
    expect(placeholderImageUrl('seed-A')).not.toBe(placeholderImageUrl('seed-B'));
  });
});

describe('roomPlaceholderUrl — variantes de habitación centralizadas', () => {
  it('cicla tags de habitación por índice (room → bedroom → living → interior → lobby)', () => {
    const expected = ['hotel,room', 'hotel,bedroom', 'hotel,living', 'hotel,interior', 'hotel,lobby'];
    for (let i = 0; i < expected.length; i++) {
      const url = roomPlaceholderUrl(7, i);
      expect(url).toContain(`/${expected[i]}?lock=`);
    }
  });

  it('vuelve a empezar la variante tras 5 habitaciones', () => {
    expect(roomPlaceholderUrl(7, 5)).toContain('/hotel,room?lock=705');
    expect(roomPlaceholderUrl(7, 6)).toContain('/hotel,bedroom?lock=706');
  });

  it('lock determinista por hotel: misma habitación siempre la misma foto', () => {
    expect(roomPlaceholderUrl(7, 2)).toBe(roomPlaceholderUrl(7, 2));
    expect(roomPlaceholderUrl(7, 2)).not.toBe(roomPlaceholderUrl(8, 2));
  });
});

describe('placeholderOrFallback', () => {
  it('usa la URL real cuando existe', () => {
    expect(placeholderOrFallback('https://cdn.example.com/foto.jpg', 1)).toBe(
      'https://cdn.example.com/foto.jpg',
    );
  });

  it('cae al placeholder loremflickr cuando la URL real es vacía o nula', () => {
    for (const empty of [null, undefined, '', '   ']) {
      const url = placeholderOrFallback(empty, 1);
      expect(url.startsWith('https://loremflickr.com/')).toBe(true);
      expect(url).toContain('/hotel,room?lock=');
    }
  });
});

describe('hotelGalleryImages — centralizado para /welcome y /search (TDD)', () => {
  it('genera 3 placeholders distintos por hotel (no 3 iguales)', () => {
    const gallery = hotelGalleryImages(1, null, 3);
    expect(gallery.length).toBe(3);
    // Las 3 deben ser URLs loremflickr distintas (mismo hotel, locks distintos)
    expect(new Set(gallery).size).toBe(3);
    expect(gallery.every((u) => u.startsWith('https://loremflickr.com/'))).toBe(true);
    // No debe colapsar a la misma URL
    expect(gallery[0]).not.toBe(gallery[1]);
    expect(gallery[1]).not.toBe(gallery[2]);
  });

  it('placeholders usan tags distintos para variedad visual real (room/bedroom/living...) — no 3× hotel,room idénticos', () => {
    const gallery = hotelGalleryImages(1, null, 3);
    const tags = gallery.map((u) => u.match(/hotel,[^?]+/)?.[0] ?? '');
    // Con el bug actual (3× mismo tag) este Set sería 1; debe ser 3
    expect(new Set(tags).size).toBe(3);
    expect(tags[0]).toContain('hotel,room');
    expect(tags[1]).toContain('hotel,bedroom');
    expect(tags[2]).toContain('hotel,living');
  });

  it('es determinista y compartido: mismo prop_id da misma galería en welcome y search', () => {
    const a = hotelGalleryImages(42, null, 3);
    const b = hotelGalleryImages(42, null, 3);
    expect(a).toEqual(b);
    // Hoteles distintos no colisionan
    expect(hotelGalleryImages(1, null, 3)).not.toEqual(hotelGalleryImages(2, null, 3));
  });

  it('incluye la imagen real primero si existe, luego los placeholders', () => {
    const withReal = hotelGalleryImages(7, 'https://cdn.test/real.jpg', 3);
    expect(withReal.length).toBe(4);
    expect(withReal[0]).toBe('https://cdn.test/real.jpg');
    expect(withReal.slice(1).every((u) => u.startsWith('https://loremflickr.com/'))).toBe(true);
    const withoutReal = hotelGalleryImages(7, null, 3);
    expect(withoutReal.length).toBe(3);
  });

  it('respeta el count pedido y el tamaño', () => {
    expect(hotelGalleryImages(1, null, 2).length).toBe(2);
    expect(hotelGalleryImages(1, 'https://cdn.test/real.jpg', 2).length).toBe(3);
    expect(hotelGalleryImages(1, null, 3, 800, 400)[0]).toContain('/800/400/');
  });
});
