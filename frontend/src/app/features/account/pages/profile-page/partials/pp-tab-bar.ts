import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({
  selector: 'app-pp-tab-bar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nav class="tab-bar">
      @for (tab of tabs(); track tab.key) {
        <button type="button" class="tab-btn" [class.is-active]="activeTab() === tab.key" (click)="setTab.emit(tab.key)">
          <span class="material-symbols-outlined tab-icon">{{ tab.icon }}</span>
          {{ tab.label }}
        </button>
      }
    </nav>
  `
})
export class PpTabBarComponent {
  readonly tabs = input.required<{ key: string; label: string; icon: string }[]>();
  readonly activeTab = input.required<string>();
  readonly setTab = output<string>();
}
