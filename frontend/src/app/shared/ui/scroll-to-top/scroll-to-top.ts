import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, inject, OnInit, signal } from '@angular/core';

@Component({
  selector: 'app-scroll-to-top',
  imports: [],
  template: `
    @if (visible()) {
      <button
        class="sst-btn"
        (click)="scrollToTop()"
        aria-label="Volver arriba"
        title="Volver arriba"
      >
        <span class="material-symbols-outlined">arrow_upward</span>
      </button>
    }
  `,
  styles: [`
    .sst-btn {
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      width: 3rem;
      height: 3rem;
      border-radius: 999px;
      border: none;
      background: var(--accent, #006076);
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.18);
      z-index: 999;
      transition: opacity 0.25s ease, transform 0.25s ease, box-shadow 0.25s ease;

      &:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 24px rgba(0, 0, 0, 0.24);
      }

      &:active {
        transform: translateY(0);
      }

      .material-symbols-outlined {
        font-size: 1.5rem;
        --icon-wght: 500;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ScrollToTopComponent implements OnInit {
  readonly visible = signal(false);
  private readonly elementRef = inject(ElementRef);
  private readonly destroyRef = inject(DestroyRef);
  private scrollEl: HTMLElement | null = null;
  private _useWindow = false;

  constructor() {
    this.destroyRef.onDestroy(() => {
      if (this.scrollEl) {
        this.scrollEl.removeEventListener('scroll', this._onScroll);
      }
      if (this._useWindow) {
        window.removeEventListener('scroll', this._onWindowScroll);
      }
    });
  }

  ngOnInit(): void {
    // Busca el ancestro scrolleable (overflow-y:auto) usado en admin/management
    // shells (.management-scroll / .system-scroll). En área huésped (public/account)
    // el scroll es el window (body), así que si no hay contenedor, hace fallback a window.
    let el: HTMLElement | null = this.elementRef.nativeElement.parentElement;
    while (el) {
      const overflowY = getComputedStyle(el).overflowY;
      if (overflowY === 'auto' || overflowY === 'scroll') {
        this.scrollEl = el;
        break;
      }
      el = el.parentElement;
    }
    if (this.scrollEl) {
      this.scrollEl.addEventListener('scroll', this._onScroll, { passive: true });
      // Estado inicial por si ya está scrolleado al montar
      this._onScroll();
    } else {
      // Fallback guest: window scroll (public/account shells no tienen contenedor scrolleable)
      this._useWindow = true;
      window.addEventListener('scroll', this._onWindowScroll, { passive: true });
      this._onWindowScroll();
    }
  }

  private _onScroll = (): void => {
    this.visible.set((this.scrollEl?.scrollTop ?? 0) > 400);
  };

  private _onWindowScroll = (): void => {
    this.visible.set(window.scrollY > 400);
  };

  scrollToTop(): void {
    if (this._useWindow) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      this.scrollEl?.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }
}

