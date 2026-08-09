import { TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';

import { SimilarCarouselComponent } from './similar-carousel';
import type { SimilarHotel } from '../../models/hotel-detail.model';

function makeSimilar(overrides: Partial<SimilarHotel> = {}): SimilarHotel {
  return {
    id: 7,
    name: 'Hotel Similar',
    stars: 4,
    reviewLabel: 'Muy bueno',
    location: 'Lima',
    similarityScore: 92,
    reason: 'Misma ciudad',
    imageUrl: 'https://cdn.example.com/similar.jpg',
    ...overrides,
  };
}

describe('SimilarCarouselComponent — galería de hoteles similares', () => {
  function setup(hotel = makeSimilar()) {
    TestBed.configureTestingModule({
      imports: [SimilarCarouselComponent],
    });
    const fixture = TestBed.createComponent(SimilarCarouselComponent);
    fixture.componentRef.setInput('hotel', hotel);
    fixture.detectChanges();
    return { fixture, comp: fixture.componentInstance };
  }

  it('compone la galería con la imagen primaria + 3 placeholders loremflickr', () => {
    const { comp } = setup();
    const gallery = comp.galleryImages();
    expect(gallery.length).toBe(4);
    expect(gallery[0]).toBe('https://cdn.example.com/similar.jpg');
    expect(gallery.slice(1).every((url) => url.startsWith('https://loremflickr.com/'))).toBe(true);
  });

  it('sin imagen real usa 3 placeholders loremflickr', () => {
    const { comp } = setup(makeSimilar({ imageUrl: '' }));
    expect(comp.galleryImages().length).toBe(3);
    expect(comp.galleryImages().every((url) => url.startsWith('https://loremflickr.com/'))).toBe(true);
  });

  it('renderiza flechas < > y puntitos cuando hay más de una imagen', () => {
    const { fixture } = setup();
    expect(fixture.debugElement.query(By.css('.sc-prev'))).toBeTruthy();
    expect(fixture.debugElement.query(By.css('.sc-next'))).toBeTruthy();
    expect(fixture.debugElement.queryAll(By.css('.sc-dot')).length).toBe(4);
  });

  it('avanzar/retroceder con wrap y clic en puntito', () => {
    const { fixture, comp } = setup();
    fixture.detectChanges();

    fixture.debugElement.query(By.css('.sc-next')).nativeElement.click();
    fixture.detectChanges();
    expect(comp.currentImageIdx()).toBe(1);

    fixture.debugElement.query(By.css('.sc-prev')).nativeElement.click();
    fixture.detectChanges();
    expect(comp.currentImageIdx()).toBe(0);

    // Wrap: desde la primera, prev va a la última
    fixture.debugElement.query(By.css('.sc-prev')).nativeElement.click();
    fixture.detectChanges();
    expect(comp.currentImageIdx()).toBe(comp.galleryImages().length - 1);

    const dots = fixture.debugElement.queryAll(By.css('.sc-dot'));
    dots[1].nativeElement.click();
    fixture.detectChanges();
    expect(comp.currentImageIdx()).toBe(1);
    expect(dots[1].nativeElement.classList.contains('active')).toBe(true);
  });

  it('una imagen que falla se descarta sin colapsar el carrusel', () => {
    const { comp } = setup();
    comp.onImgError({ src: 'https://cdn.example.com/similar.jpg' } as HTMLImageElement);
    expect(comp.galleryImages().length).toBe(3);
    expect(comp.galleryImages().every((u) => u.startsWith('https://loremflickr.com/'))).toBe(true);
  });

  it('muestra el icono hotel cuando toda la galería falla', () => {
    const { fixture, comp } = setup();
    comp.galleryImages().forEach((url) => comp.onImgError({ src: url } as HTMLImageElement));
    fixture.detectChanges();
    expect(comp.galleryImages().length).toBe(0);
    expect(fixture.debugElement.query(By.css('.sc-prev'))).toBeNull();
    expect(fixture.nativeElement.querySelector('.material-symbols-outlined')?.textContent).toBe('hotel');
  });
});
