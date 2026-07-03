import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({
  selector: 'app-co-step-breadcrumb',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="co-steps">
      @for (s of steps(); track s.num; let first = $first) {
        @if (!first) { <div class="co-step-connector" [class.active]="currentStep() >= s.num"></div> }
        <button class="co-step" [class.active]="currentStep() === s.num" [class.done]="currentStep() > s.num"
          (click)="goToStep.emit(s.num)" [disabled]="currentStep() < s.num && !canGoNext()">
          <span class="co-step-num">
            @if (currentStep() > s.num) { <span class="material-symbols-outlined">check</span> }
            @else { <span class="material-symbols-outlined">{{ s.icon }}</span> }
          </span>
          <span class="co-step-label">{{ s.label }}</span>
        </button>
      }
    </div>
  `
})
export class CoStepBreadcrumbComponent {
  readonly steps = input<any[]>([]);
  readonly currentStep = input(1);
  readonly canGoNext = input(false);
  readonly goToStep = output<number>();
}
