import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';

import {
  hotelGalleryImages,
} from '../../../../shared/utils/placeholder-image.util';
import { CarouselControlsComponent } from '../../../../shared/ui/carousel-controls/carousel-controls';
import type { SimilarHotel } from '../../models/hotel-detail.model';

@Component({
  selector: 'app-similar-carousel',
  imports: [CarouselControlsComponent],
  templateUrl: './similar-carousel.html',
  styleUrl: './similar-carousel.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SimilarCarouselComponent {
  readonly hotel = input.required<SimilarHotel>();

  readonly currentImageIdx = signal(0);

  /** URLs cuya carga falló — se filtran de la galería sin colapsarla. */
  private readonly failedImageSrcs = signal<Set<string>>(new Set());

  /** Galería centralizada — mismo `hotelGalleryImages` que `/welcome` y `/search`. */
  readonly galleryImages = computed(() => {
    const h = this.hotel();
    const failed = this.failedImageSrcs();
    return hotelGalleryImages(h.id, h.imageUrl, 3).filter(
      (url) => !failed.has(this.resolveUrl(url)),
    );
  });

  readonly stripOffset = computed(() => {
    if (this.galleryImages().length <= 1) return '';
    return `translateX(-${this.currentImageIdx() * 100}%)`;
  });

  goToImage(idx: number) {
    this.currentImageIdx.set(idx);
  }

  prevImage() {
    this.stepImage(-1);
  }

  nextImage() {
    this.stepImage(1);
  }

  private stepImage(dir: 1 | -1) {
    const total = this.galleryImages().length;
    if (total <= 1) return;
    this.currentImageIdx.set((this.currentImageIdx() + dir + total) % total);
  }

  /** Normaliza URLs (relativas → absolutas) para comparar src de <img> con la galería. */
  private resolveUrl(url: string): string {
    try {
      return new URL(url, window.location.origin).href;
    } catch {
      return url;
    }
  }

  onImgError(img: HTMLImageElement | null) {
    const src = img?.currentSrc || img?.src || '';
    if (!src) return;
    this.failedImageSrcs.update((failed) => new Set(failed).add(this.resolveUrl(src)));
  }
}
