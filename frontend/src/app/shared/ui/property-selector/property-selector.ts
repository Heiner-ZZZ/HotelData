import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  EventEmitter,
  HostListener,
  inject,
  Input,
  OnInit,
  OnChanges,
  Output,
  SimpleChanges,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { debounceTime, distinctUntilChanged, Subject } from 'rxjs';

import type { PropertyOption, PropertyOptionsPage } from '../../models/property-option.model';
import { PropertySelectorService } from '../../services/property-selector.service';

@Component({
  selector: 'app-property-selector',
  imports: [],
  templateUrl: './property-selector.html',
  styleUrl: './property-selector.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PropertySelectorComponent implements OnInit, OnChanges {
  private readonly service = inject(PropertySelectorService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly filter$ = new Subject<string>();

  @Input() selectedPropId = 0;
  @Input() selectedLabel = '';

  @Output() propIdChange = new EventEmitter<number>();

  readonly dropdownOpen = signal(false);
  readonly filterText = signal('');
  readonly propertyOptions = signal<PropertyOption[]>([]);
  readonly propertyLoading = signal(false);

  private page = 1;
  private hasNext = false;
  private searchValue = '';

  ngOnInit() {
    this.loadInitialPage();

    this.filter$
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe((term) => {
        this.searchValue = term;
        this.page = 1;
        this.propertyLoading.set(true);
        this.service
          .getOptions(term || undefined, 1, 10)
          .pipe(takeUntilDestroyed(this.destroyRef))
          .subscribe({
            next: (result) => {
              this.propertyOptions.set(result.items);
              this.hasNext = result.hasNext;
              this.page = 1;
              this.propertyLoading.set(false);
              this.dropdownOpen.set(true);
            },
            error: () => this.propertyLoading.set(false),
          });
      });
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['selectedLabel'] && this.selectedLabel) {
      this.filterText.set(this.selectedLabel);
    }
  }

  private loadInitialPage() {
    this.propertyLoading.set(true);
    this.service
      .getOptions('', 1, 10)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.propertyOptions.set(result.items);
          this.hasNext = result.hasNext;
          this.propertyLoading.set(false);
        },
        error: () => this.propertyLoading.set(false),
      });
  }

  onFilterChange(value: string) {
    this.filterText.set(value);
    this.filter$.next(value);
  }

  selectProperty(option: PropertyOption) {
    this.filterText.set(option.label);
    this.dropdownOpen.set(false);
    this.propIdChange.emit(option.propId);
  }

  @HostListener('document:click', ['$event'])
  closeDropdown(event: Event) {
    const target = event.target as HTMLElement;
    if (!target.closest('.ps-autocomplete')) {
      this.dropdownOpen.set(false);
    }
  }

  onInputFocus() {
    this.dropdownOpen.set(true);
  }

  onScroll(event: Event) {
    const el = event.target as HTMLElement;
    const threshold = 10;
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - threshold && this.hasNext && !this.propertyLoading()) {
      this.loadMore();
    }
  }

  private loadMore() {
    if (!this.hasNext || this.propertyLoading()) return;
    this.propertyLoading.set(true);
    this.page++;
    this.service
      .getOptions(this.searchValue || undefined, this.page, 10)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.propertyOptions.update((prev) => [...prev, ...result.items]);
          this.hasNext = result.hasNext;
          this.propertyLoading.set(false);
        },
        error: () => {
          this.page--;
          this.propertyLoading.set(false);
        },
      });
  }
}
