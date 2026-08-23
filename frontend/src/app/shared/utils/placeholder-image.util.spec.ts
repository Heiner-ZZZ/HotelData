import {
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
