import { ChangeDetectionStrategy, Component, computed, DestroyRef, ElementRef, inject, input, output, signal, viewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CdkDragDrop, CdkDropList, CdkDrag, moveItemInArray } from '@angular/cdk/drag-drop';
import { isDevMode } from '@angular/core';
import { ConfirmDialogService } from '../../../../../shared/ui/confirm-dialog/confirm-dialog.service';
import { PropertiesApiService } from '../../../services/properties-api.service';

export interface GalleryImage {
  imageUrl: string;
  title: string;
}

@Component({
  selector: 'app-image-gallery',
  imports: [CdkDropList, CdkDrag],
  templateUrl: './image-gallery.html',
  styleUrl: './image-gallery.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImageGalleryComponent {
  private readonly destroyRef = inject(DestroyRef);
  private readonly confirmDialog = inject(ConfirmDialogService);
  private readonly propertiesApi = inject(PropertiesApiService);

  readonly propId = input.required<number>();
  readonly images = input.required<GalleryImage[]>();
  readonly maxImages = input(10);

  readonly imagesChange = output<GalleryImage[]>();
  readonly errorChange = output<string>();

  readonly selectedFile = signal<File | null>(null);
  readonly imagePreviewUrl = signal<string | null>(null);
  readonly fileInput = viewChild<ElementRef<HTMLInputElement>>('fileInput');

  /** URLs de imágenes que fallaron al cargar (404, host caído, placeholder demo). */
  readonly brokenImages = signal<Set<string>>(new Set());

  private autoSaveTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly AUTO_SAVE_DEBOUNCE_MS = 400;

  readonly imageCountLabel = computed(() => {
    const len = this.images().length;
    const max = this.maxImages();
    if (len >= max) return `${len} / ${max} — Límite alcanzado`;
    if (len >= max - 2) return `${len} / ${max} — Cerca del límite`;
    return `${len} / ${max}`;
  });

  readonly showReorderHint = computed(() => this.images().length > 1);

  /** Marca la imagen como rota para mostrar el fallback en vez de un img colgado. */
  onImgError(imageUrl: string) {
    this.brokenImages.update((set) => new Set(set).add(imageUrl));
  }

  triggerFileInput() {
    this.fileInput()?.nativeElement.click();
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      this.errorChange.emit('Solo se permiten archivos de imagen.');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      this.errorChange.emit('La imagen no puede superar los 10 MB.');
      return;
    }

    this.selectedFile.set(file);
    this.errorChange.emit('');

    const reader = new FileReader();
    reader.onload = () => {
      this.imagePreviewUrl.set(reader.result as string);
    };
    reader.readAsDataURL(file);
  }

  clearSelectedFile() {
    this.selectedFile.set(null);
    this.imagePreviewUrl.set(null);
    if (this.fileInput()?.nativeElement) {
      this.fileInput()!.nativeElement.value = '';
    }
  }

  addImage() {
    const file = this.selectedFile();
    if (!file) return;
    const current = this.images();

    if (current.length >= this.maxImages()) {
      this.errorChange.emit(`Máximo ${this.maxImages()} imágenes por propiedad.`);
      return;
    }

    this.propertiesApi.uploadImage(this.propId(), file).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (result: any) => {
        this.errorChange.emit('');
        this.imagesChange.emit([...current, { imageUrl: result.image_url, title: result.title || '' }]);
        this.clearSelectedFile();
      },
      error: (err) => {
        if (isDevMode()) console.error('Error uploading image', err);
        const msg = err?.error?.detail || err?.message || 'Error al subir la imagen. Intenta de nuevo.';
        this.errorChange.emit(msg);
      },
    });
  }

  addImageByUrl(url: string) {
    const trimmed = url.trim();
    if (!trimmed) {
      this.errorChange.emit('Introduce una URL válida.');
      return;
    }
    const current = this.images();
    if (current.length >= this.maxImages()) {
      this.errorChange.emit(`Máximo ${this.maxImages()} imágenes por propiedad.`);
      return;
    }
    this.propertiesApi.addImage(this.propId(), trimmed, '').pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.errorChange.emit('');
        this.imagesChange.emit([...current, { imageUrl: trimmed, title: '' }]);
      },
      error: (err) => {
        if (isDevMode()) console.error('Error adding image by URL', err);
        const msg = err?.error?.detail || err?.message || 'Error al añadir imagen por URL.';
        this.errorChange.emit(msg);
      },
    });
  }

  async removeImage(imageUrl: string) {
    const ok = await this.confirmDialog.open({
      title: 'Eliminar imagen',
      message: '¿Eliminar esta imagen de la galería?',
      confirmLabel: 'Eliminar',
      variant: 'danger',
      mode: 'delete',
      modeDetail: 'Imagen de galería',
    });
    if (!ok) return;
    const current = this.images();
    this.propertiesApi.deleteImage(this.propId(), imageUrl).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.errorChange.emit('');
        this.imagesChange.emit(current.filter((i) => i.imageUrl !== imageUrl));
      },
      error: (err) => {
        if (isDevMode()) console.error('Error removing image', err);
        this.errorChange.emit('Error al eliminar imagen. Intenta de nuevo.');
      },
    });
  }

  onDrop(event: CdkDragDrop<GalleryImage[]>) {
    const current = this.images();
    const images = [...current];
    moveItemInArray(images, event.previousIndex, event.currentIndex);
    this.imagesChange.emit(images);

    if (this.autoSaveTimer !== null) {
      clearTimeout(this.autoSaveTimer);
    }
    this.autoSaveTimer = setTimeout(() => {
      this.autoSaveTimer = null;
      const order = images.map((i) => i.imageUrl);
      this.propertiesApi.reorderImages(this.propId(), order).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (result) => {
          this.imagesChange.emit(result.images.map((i: any) => ({ imageUrl: i.image_url, title: i.title || '' })));
        },
        error: (err) => {
          if (isDevMode()) console.error('Error saving image order', err);
          this.errorChange.emit('Error al guardar el orden de imágenes.');
        },
      });
    }, this.AUTO_SAVE_DEBOUNCE_MS);
  }
}
