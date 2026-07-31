import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  HostListener,
  inject,
  input,
  output,
  signal,
  untracked,
} from '@angular/core';
import { httpResource } from '@angular/common/http';

import type { PropertyOption } from '../../models/property-option.model';
import { PropertyContextService } from '../../services/property-context.service';
import { PropertySelectorService } from '../../services/property-selector.service';

interface PropertyOptionsDto {
  properties: { prop_id: number; display_name: string }[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

interface SearchResult {
  items: PropertyOption[];
  total: number;
  page: number;
  pageSize: number;
  hasNext: boolean;
}

@Component({
  selector: 'app-property-selector',
  imports: [],
  templateUrl: './property-selector.html',
  styleUrl: './property-selector.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PropertySelectorComponent {
  /**
   * `PropertyContextService` — public so the template can bind
   * `@else if (ctx.mode() === 'none')`. Angular 22's AOT compiler enforces
   * `private` strictly (the dev JIT compiler is more lenient) so this MUST stay
   * non-private. Fields consumed by the template: `visible`, `singleMode`,
   * `loading`, `singleModeLoading`, `singleHotelLabel` (all `computed`).
   */
  readonly ctx = inject(PropertyContextService);
  /** Selected property ID — receives initial value from parent and updates on (propIdChange). */
  readonly selectedPropId = input(0);
  /** Selected property label — drives the search-box autofill via the parent-sync effect below. */
  readonly selectedLabel = input('');

  /** Emits when the user picks a new property. Parent should react and update selectedPropId/selectedLabel. */
  readonly propIdChange = output<{ propId: number; label: string }>();

  readonly dropdownOpen = signal(false);
  /**
   * Writable mirror of `selectedLabel()` plus local overrides via `.set()`.
   * We deliberately use a plain `signal` instead of `linkedSignal(() => selectedLabel())`
   * to avoid the NG0600 re-entrancy that the previous `toObservable(filterText)` chain
   * triggered. The parent-sync effect below mirrors `selectedLabel()` into `filterText`
   * with `untracked()` writes so the effect only fires on parent label changes.
   */
  readonly filterText = signal('');

  readonly propertyOptions = signal<PropertyOption[]>([]);
  readonly propertyLoading = signal(false);
  readonly authRequired = signal(false);

  /** True once the component has finished its context-aware initialization. */
  private readonly initialized = signal(false);

  // ── Pagination + debounce state (signals drive httpResource refire) ──
  readonly page = signal(1);
  readonly hasNext = signal(false);
  private readonly debouncedTerm = signal('');

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
      const defaultId = this.ctx.defaultPropId();
      if (defaultId) {
        const assigned = this.ctx.assignedProperties().find((p) => p.propId === defaultId);
        if (assigned?.label) return assigned.label;
      }
      return this.ctx.currentPropLabel() || this.selectedLabel() || '';
    }
    return '';
  });

  /** True while the context hasn't loaded yet — show subtle loading indicator. */
  readonly loading = computed(() => !this.ctx.ready());

  /** True while single mode is loading — show subtle indicator instead of empty space. */
  readonly singleModeLoading = computed(() => !this.ctx.ready());

  // ── Reactive search resource — replaces legacy `service.getOptions().subscribe(...)` ──
  /**
   * Page=1 + first emit are gated by `debouncedTerm` + `page`. Initially both
   * are empty/1 so `httpResource` returns `undefined` (no fetch during mount).
   * The first non-debounced sync from `selectedLabel()` writes `debouncedTerm`
   * only AFTER the debounce effect timer fires (300ms after the user stops
   * typing), preventing an unwanted network call at boot.
   */
  readonly searchResource = httpResource<SearchResult>(() => {
    // Guard: do NOT fetch on mount or in 'single'/'multi' modes (legacy `skip(1)`
    // semantic). The fetch fires only after `initFromContext` has set `initialized`
    // true AND — in 'all' mode — explicitly bumped `debouncedTerm + page=1`.
    if (!this.initialized()) return undefined;
    return {
      url: `/api/management/properties/options?q=${encodeURIComponent(this.debouncedTerm() || '')}&page=${this.page()}&page_size=10`,
      method: 'GET' as const,
      withCredentials: true,
    };
  }, {
    parse: (dto) => {
      const raw = dto as PropertyOptionsDto;
      return {
        items: raw.properties.map((p) => ({
          propId: p.prop_id,
          label: p.display_name || `Hotel ${p.prop_id}`,
        })),
        total: raw.total,
        page: raw.page,
        pageSize: raw.page_size,
        hasNext: raw.has_next,
      };
    },
  });

  constructor() {
    // ── Parent sync: mirror `selectedLabel()` into `filterText` on input changes ──
    // `untracked()` around the write so this effect only subscribes to
    // `selectedLabel()` (not to its own write into `filterText`).
    let lastSeenLabel: string | null = null;
    effect(() => {
      const label = this.selectedLabel();
      if (label === lastSeenLabel) return;
      lastSeenLabel = label;
      untracked(() => {
        if (this.filterText() !== label) this.filterText.set(label);
      });
    });

    // ── Debounce user input ──
    // Replaces the legacy `toObservable(filterText).pipe(skip(1), debounceTime(300),
    // distinctUntilChanged())` chain. `onCleanup` cancels any pending timer when
    // the user types again (mirrors the trailing-edge semantics of `debounceTime`).
    // `firstSearchRun` preserves the legacy `skip(1)` semantic: the very first
    // effect invocation (boot-time sync via the parent-sync effect above)
    // does NOT push the initial label into `debouncedTerm` — only subsequent
    // user-typed changes do. In 'all' mode the initial fetch is triggered
    // explicitly by `initFromContext` setting `debouncedTerm=''`+`page=1`.
    let firstSearchRun = true;
    effect((onCleanup) => {
      const term = this.filterText();
      if (firstSearchRun) {
        firstSearchRun = false;
        return;
      }
      const timer = setTimeout(() => {
        this.debouncedTerm.set(term);
        this.page.set(1);
      }, 300);
      onCleanup(() => clearTimeout(timer));
    });

    // ── Bridge: searchResource.value() → component state ──
    // Page=1 → REPLACE items; page>1 → APPEND (after dedup). Single signal
    // holds the cumulative list so `loadMore` doesn't need its own subscribe.
    effect(() => {
      const r = this.searchResource.value();
      if (!r) return;
      if (this.page() === 1) {
        // Fresh search results: REPLACE and OPEN dropdown so user sees matches.
        this.propertyOptions.set(r.items);
        this.dropdownOpen.set(true);
      } else {
        // loadMore (page>1): APPEND only — do NOT reopen a dropdown the user
        // explicitly closed (e.g. via the Document:click listener).
        // [FIX] `untracked()` around the read breaks the self-write re-entrancy
        // (effect would otherwise depend on `propertyOptions` AND write to it
        // in the same pass, triggering NG0600 producerRecomputeValue storm).
        const existing = new Set(
          untracked(() => this.propertyOptions()).map((o) => o.propId),
        );
        const fresh = r.items.filter((item) => !existing.has(item.propId));
        this.propertyOptions.update((prev) => [...prev, ...fresh]);
      }
      this.hasNext.set(r.hasNext);
      this.propertyLoading.set(false);
      this.authRequired.set(false);
    });

    // ── Bridge: searchResource.error() → graceful 401 handling, loading reset ──
    effect(() => {
      const err = this.searchResource.error();
      if (!err) return;
      const status =
        typeof err === 'object' && err !== null && 'status' in err
          ? (err as { status?: number }).status
          : undefined;
      if (status === 401) {
        this.authRequired.set(true);
        this.propertyLoading.set(false);
        this.dropdownOpen.set(false);
      } else {
        this.propertyLoading.set(false);
      }
    });

    // ── Bootstrap: trigger initial fetch in 'all' mode after ctx is ready ──
    // [FIX] `untracked()` around `initFromContext()` prevents NG0600 self-write
    // re-entrancy: the effect reads `initialized()` to decide whether to call
    // `initFromContext()`, and the very first line of `initFromContext()` writes
    // `initialized.set(true)`. Without `untracked()`, the producerRecomputeValue
    // → equal → value chain fires on every component mount.
    effect(() => {
      if (this.ctx.ready() && !this.initialized()) {
        untracked(() => this.initFromContext());
      }
    });
  }

  private initFromContext() {
    if (this.initialized()) return;
    this.initialized.set(true);

    // --- Modo single: etiqueta estatica, auto-emitir ---
    if (this.ctx.mode() === 'single') {
      const propId = this.ctx.defaultPropId();
      const defaultProp = this.ctx.assignedProperties().find((p) => p.propId === propId);
      const label = defaultProp?.label || this.ctx.currentPropLabel();
      if (label) this.filterText.set(label);
      this.propIdChange.emit({ propId, label });
      return;
    }

    // --- Modo multi: cargar propiedades asignadas sin llamar a la API ---
    if (this.ctx.mode() === 'multi') {
      const assigned = this.ctx.assignedProperties();
      if (assigned.length > 0) {
        this.propertyOptions.set(assigned.map((p) => ({ propId: p.propId, label: p.label })));
        this.hasNext.set(false);
        if (assigned.length === 1 && !this.selectedPropId()) {
          this.filterText.set(assigned[0].label);
          this.propIdChange.emit({ propId: assigned[0].propId, label: assigned[0].label });
          return;
        }
      }
      return;
    }

    // --- Modo all (super_admin): el resource auto-fires al setear `debouncedTerm` + `page=1` ---
    this.debouncedTerm.set('');
    this.page.set(1);
  }

  onFilterChange(value: string) {
    this.filterText.set(value);
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
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - threshold && this.hasNext() && !this.propertyLoading()) {
      this.loadMore();
    }
  }

  /** httpResource auto-refires when `page()` increments (searchResource URL formula reads it). */
  private loadMore() {
    if (!this.hasNext() || this.propertyLoading()) return;
    this.propertyLoading.set(true);
    this.page.update((p) => p + 1);
  }
}
