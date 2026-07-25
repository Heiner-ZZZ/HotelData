import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  effect,
  HostListener,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { CdkTrapFocus } from '@angular/cdk/a11y';

@Component({
  selector: 'app-image-lightbox',
  standalone: true,
  imports: [CdkTrapFocus],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (isOpen() || closing()) {
      <div
        class="image-lightbox"
        [class.image-lightbox--open]="isOpen() && !closing()"
        [class.image-lightbox--closing]="closing()"
        (click)="close()"
        cdkTrapFocus
        [cdkTrapFocusAutoCapture]="true"
        role="dialog"
        aria-modal="true"
        [attr.aria-label]="ariaLabel()"
      >
        <button
          type="button"
          class="image-lightbox__close"
          (click)="close(); $event.stopPropagation()"
          aria-label="Cerrar"
        >
          <span class="material-symbols-outlined">close</span>
        </button>

        <img
          [src]="imageUrl()"
          [alt]="altText()"
          class="image-lightbox__image"
          (click)="$event.stopPropagation()"
        />
      </div>
    }
  `,
  styles: `
    :host {
      display: contents;
    }

    .image-lightbox {
      position: fixed;
      inset: 0;
      z-index: 1000;
      display: grid;
      place-items: center;
      background: color-mix(in srgb, var(--app-bg) 95%, transparent);
      backdrop-filter: blur(6px);
      padding: 24px;
      opacity: 0;
      transform: scale(0.96);
      transition: opacity 200ms ease, transform 200ms ease;
      cursor: zoom-out;

      &--open {
        opacity: 1;
        transform: scale(1);
      }

      &--closing {
        opacity: 0;
        transform: scale(0.96);
      }

      &__close {
        position: absolute;
        top: 16px;
        right: 16px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 44px;
        height: 44px;
        border: none;
        border-radius: 50%;
        background: var(--surface-raised);
        color: var(--app-text);
        cursor: pointer;
        box-shadow: var(--shadow-md);
        transition: background 0.2s ease, transform 0.2s ease;
        z-index: 1001;

        &:hover {
          background: var(--surface-hover);
          transform: scale(1.05);
        }

        &:focus-visible {
          outline: 2px solid var(--accent);
          outline-offset: 2px;
        }
      }

      &__image {
        max-width: 90vw;
        max-height: 85vh;
        border-radius: 12px;
        box-shadow: var(--shadow-md);
        object-fit: contain;
        cursor: default;
      }
    }
  `,
})
export class ImageLightboxComponent {
  private readonly destroyRef = inject(DestroyRef);

  readonly imageUrl = input.required<string>();
  readonly altText = input<string>('Imagen ampliada');
  readonly isOpen = input<boolean>(false);
  readonly ariaLabel = input<string>('Vista ampliada de imagen');

  readonly closed = output<void>();

  readonly closing = signal(false);

  private previousActiveElement: Element | null = null;

  constructor() {
    effect(() => {
      if (this.isOpen()) {
        this.previousActiveElement = document.activeElement;
        document.body.style.overflow = 'hidden';
      } else {
        document.body.style.overflow = '';
        this.restoreFocus();
      }
    });

    this.destroyRef.onDestroy(() => {
      document.body.style.overflow = '';
      this.restoreFocus();
    });
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.isOpen()) {
      this.close();
    }
  }

  close(): void {
    if (this.closing()) return;
    this.closing.set(true);
    window.setTimeout(() => {
      this.closed.emit();
      this.closing.set(false);
    }, 200);
  }

  private restoreFocus(): void {
    const el = this.previousActiveElement as HTMLElement | null;
    this.previousActiveElement = null;
    if (
      el &&
      typeof el.focus === 'function' &&
      el.isConnected &&
      !el.hasAttribute('disabled') &&
      (el as HTMLElement).tabIndex !== -1
    ) {
      el.focus({ preventScroll: true });
    }
  }
}
