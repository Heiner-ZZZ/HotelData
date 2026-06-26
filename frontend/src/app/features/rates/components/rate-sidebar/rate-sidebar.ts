import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

export interface SidebarSection {
  id: string;
  label: string;
  icon: string;
  badge?: number;
}

@Component({
  selector: 'app-rate-sidebar',
  imports: [],
  templateUrl: './rate-sidebar.html',
  styleUrl: './rate-sidebar.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RateSidebarComponent {
  readonly sections = input<SidebarSection[]>([]);
  readonly activeSection = input<string>('');
  readonly sectionChange = output<string>();

  select(id: string): void {
    this.sectionChange.emit(id);
  }
}
