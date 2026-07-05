import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { FormGroup, ReactiveFormsModule } from '@angular/forms';

@Component({
  selector: 'app-reservations-filters-bar',
  standalone: true,
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  templateUrl: './reservations-filters-bar.html',
  styleUrl: './reservations-filters-bar.scss',
})
export class ReservationsFiltersBarComponent {
  readonly dateForm = input.required<FormGroup>();
  readonly currentFolioFilter = input('');
  readonly currentStayStatusFilter = input('');
  readonly currentSourceFilter = input('');
  readonly hasActiveFilters = input(false);

  readonly navigateDate = output<number>();
  readonly goToday = output<void>();
  readonly applyFilter = output<void>();
  readonly folioSearch = output<string>();
  readonly stayStatusFilter = output<string>();
  readonly sourceFilter = output<string>();
  readonly clearAllFilters = output<void>();

  protected onFolioSearch(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.folioSearch.emit(value);
  }

  protected onStayStatusFilter(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.stayStatusFilter.emit(value);
  }

  protected onSourceFilter(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.sourceFilter.emit(value);
  }
}
