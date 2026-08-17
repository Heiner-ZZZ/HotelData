import { ChangeDetectionStrategy, Component, ElementRef, HostListener, inject, signal } from '@angular/core';
import { Router } from '@angular/router';

import { ActiveTurnoService } from '../../services/active-turno.service';

@Component({
  selector: 'app-turno-chip',
  imports: [],
  templateUrl: './turno-chip.html',
  styleUrl: './turno-chip.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TurnoChipComponent {
  readonly service = inject(ActiveTurnoService);
  private readonly router = inject(Router);
  private readonly elementRef = inject(ElementRef);

  readonly isOpen = signal(false);

  readonly vm = this.service.viewModel;
  readonly isLoading = this.service.isLoading;
  readonly hasError = this.service.hasError;
  readonly hasMultiple = this.service.hasMultiple;

  toggle(): void {
    this.isOpen.update((v) => !v);
  }

  close(): void {
    this.isOpen.set(false);
  }

  /** Cycle caja ↔ personal ("tipo bucle") via the ">" button. */
  cycleKind(): void {
    this.service.cycleKind();
    this.close();
  }

  onCtaClick(href: string): void {
    this.close();
    void this.router.navigateByUrl(href);
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.close();
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.isOpen()) return;
    const host = this.elementRef.nativeElement as HTMLElement;
    if (!host.contains(event.target as Node)) {
      this.close();
    }
  }
}
