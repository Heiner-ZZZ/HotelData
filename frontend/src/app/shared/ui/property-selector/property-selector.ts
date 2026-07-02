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
  computed,
  effect,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { debounceTime, distinctUntilChanged, Subject } from 'rxjs';

import type { PropertyOption } from '../../models/property-option.model';
import { PropertyContextService } from '../../services/property-context.service';
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
  readonly ctx = inject(PropertyContextService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly filter$ = new Subject<string>();

  @Input() selectedPropId = 0;
  @Input() selectedLabel = '';

  @Output() propIdChange = new EventEmitter<{ propId: number; label: string }>();

  readonly dropdownOpen = signal(false);
  readonly filterText = signal('');
  readonly propertyOptions = signal<PropertyOption[]>([]);
  readonly propertyLoading = signal(false);
  readonly authRequired = signal(false);

  /** True once the component has finished its context-aware initialization. */
  private readonly initialized = signal(false);

  private page = 1;
  private hasNext = false;
  private searchValue = '';

  /** Whether the selector should be visible as a full dropdown. */
  readonly visible = computed(() => {
    const mode = this.ctx.mode();
    return mode === 'all' || mode === 'multi';
  });

  /** Whether the selector should show a static label (single-hotel mode). */
  readonly singleMode = computed(() => this.ctx.mode() === 'single');

  /** The static hotel label for single-hotel mode. */
  readonly singleHotelLabel = computed(() => {
    if (!this.ctx.ready()) return '';
    if (this.ctx.singleHotelMode()) {
      return this.ctx.currentPropLabel() || this.selectedLabel || 'Hotel asignado';
    }
    return '';
  });

  constructor() {
    // React to context becoming ready (async HTTP call)
    // This effect runs when ctx.ready() changes to true.
    effect(() => {
      if (this.ctx.ready() && !this.initialized()) {
        this.initFromContext();
      }
    });
  }

  ngOnInit() {
    // If context is already ready, initFromContext will be called by the effect
  }

  private initFromContext() {
    if (this.initialized()) return;
    this.initialized.set(true);

    // --- Modo single: etiqueta estatica, auto-emitir ---
    if (this.ctx.mode() === 'single') {
      const label = this.ctx.currentPropLabel();
      if (label) this.filterText.set(label);
      if (this.selectedPropId !== this.ctx.currentPropId()) {
        this.propIdChange.emit({
          propId: this.ctx.currentPropId(),
          label: this.ctx.currentPropLabel(),
        });
      }
      return;
    }

    // --- Modo multi: cargar propiedades asignadas sin llamar a la API ---
    if (this.ctx.mode() === 'multi') {
      const assigned = this.ctx.assignedProperties();
      if (assigned.length > 0) {
        this.propertyOptions.set(assigned.map((p) => ({ propId: p.propId, label: p.label })));
        this.hasNext = false;
        // Si solo hay una asignada, auto-seleccionar
        if (assigned.length === 1 && !this.selectedPropId) {
          this.filterText.set(assigned[0].label);
          this.propIdChange.emit({ propId: assigned[0].propId, label: assigned[0].label });
          return;
        }
      }
      return; // No llamar loadInitialPage — ya tenemos los datos
    }

    // --- Modo all (super_admin): cargar normalmente desde la API ---
    this.loadInitialPage();

    this.filter$
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe((term) => {
        this.searchValue = term;
        this.page = 1;
        this.loadPage();
      });
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes['selectedLabel'] && this.selectedLabel) {
      this.filterText.set(this.selectedLabel);
    }
  }

  private loadInitialPage() {
    this.searchValue = '';
    this.page = 1;
    this.loadPage();
  }

  private loadPage() {
    this.propertyLoading.set(true);
    this.service
      .getOptions(this.searchValue || undefined, this.page, 10)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          if (result.authRequired) {
            this.authRequired.set(true);
            this.propertyLoading.set(false);
            this.dropdownOpen.set(false);
            return;
          }
          this.authRequired.set(false);
          this.propertyOptions.set(result.items);
          this.hasNext = result.hasNext;
          this.propertyLoading.set(false);
          this.dropdownOpen.set(true);
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
    this.propIdChange.emit({ propId: option.propId, label: option.label });
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
