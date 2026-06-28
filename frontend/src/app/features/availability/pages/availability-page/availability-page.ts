import { ChangeDetectionStrategy, Component, HostListener, inject } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';

import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { AvailabilityCalendarComponent } from '../../components/availability-calendar/availability-calendar';
import { AvailabilityQuickActionsComponent } from '../../components/availability-quick-actions/availability-quick-actions';
import { AvailabilityDataTablesComponent } from '../../components/availability-data-tables/availability-data-tables';
import { AvailabilityStore } from '../../services/availability.store';

@Component({
  selector: 'app-availability-page',
  imports: [
    AvailabilityCalendarComponent,
    AvailabilityDataTablesComponent,
    AvailabilityQuickActionsComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    PropertySelectorComponent,
    ReactiveFormsModule,
  ],
  providers: [AvailabilityStore],
  templateUrl: './availability-page.html',
  styleUrl: './availability-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AvailabilityPageComponent {
  readonly store = inject(AvailabilityStore);

  @HostListener('document:keydown', ['$event'])
  handleKeyboard(event: KeyboardEvent) {
    const tag = (event.target as HTMLElement)?.tagName;
    const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';

    if (event.key === 'Escape') {
      if (isInput) return;
      event.preventDefault();
      this.store.handleEscape();
      return;
    }

    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
      if (isInput || this.store.multiSelectMode() || this.store.saving()) return;
      event.preventDefault();
      this.store.navigateArrow(event.key);
    }
  }
}
