import { ChangeDetectionStrategy, Component, ElementRef, inject, OnDestroy, OnInit, signal } from '@angular/core';

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
        font-variation-settings: 'FILL' 0, 'wght' 500, 'GRAD' 0, 'opsz' 24;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ScrollToTopComponent implements OnInit, OnDestroy {
  readonly visible = signal(false);
  private readonly elementRef = inject(ElementRef);
  private scrollEl: HTMLElement | null = null;

  ngOnInit(): void {
    // Find the nearest scrollable ancestor (the overflow-y:auto container)
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
    }
  }

  ngOnDestroy(): void {
    if (this.scrollEl) {
      this.scrollEl.removeEventListener('scroll', this._onScroll);
    }
  }

  private _onScroll = (): void => {
    this.visible.set((this.scrollEl?.scrollTop ?? 0) > 400);
  };

  scrollToTop(): void {
    this.scrollEl?.scrollTo({ top: 0, behavior: 'smooth' });
  }
}
