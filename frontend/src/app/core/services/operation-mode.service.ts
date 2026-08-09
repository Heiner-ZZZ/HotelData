import { computed, DestroyRef, inject, Injectable, signal } from '@angular/core';
import { NavigationEnd, NavigationStart, Router } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { filter } from 'rxjs';

/** Modo CRUD actual mostrado en el nav superior. `execute` cubre acciones
 * fuera del flujo CRUD normal (ETL, validaciones, detención de procesos). */
export type OperationMode = 'read' | 'insert' | 'update' | 'delete' | 'execute';

export interface OperationModeInfo {
  mode: OperationMode;
  label: string;
  description: string;
  color: string;
  severity: number;
  detail?: string;
}

export interface OperationModeRouteData {
  operationMode?: OperationMode;
  operationDetail?: string;
}

const MODE_INFO: Record<OperationMode, Omit<OperationModeInfo, 'mode' | 'detail'>> = {
  read: {
    label: 'Solo lectura',
    description: 'Estás viendo información sin modificar nada.',
    color: 'var(--success)',
    severity: 0,
  },
  insert: {
    label: 'Creando',
    description: 'Estás registrando información nueva en el sistema.',
    color: 'var(--warning)',
    severity: 1,
  },
  update: {
    label: 'Editando',
    description: 'Estás modificando información existente. El estado anterior queda solo en el log.',
    color: 'color-mix(in srgb, var(--warning) 45%, var(--danger) 55%)',
    severity: 2,
  },
  delete: {
    label: 'Eliminando',
    description: 'Estás eliminando información. Es un borrado lógico, pero afecta de forma permanente.',
    color: 'var(--danger)',
    severity: 3,
  },
  execute: {
    label: 'Ejecutando',
    description: 'Estás ejecutando una acción fuera del flujo CRUD normal (ETL, validación o detención de procesos).',
    color: '#8b5cf6',
    severity: 2,
  },
};

@Injectable({ providedIn: 'root' })
export class OperationModeService {
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  /** Stable mode owned by the active route. */
  private readonly pageModeSignal = signal<OperationModeInfo>({
    mode: 'read',
    label: MODE_INFO.read.label,
    description: MODE_INFO.read.description,
    color: MODE_INFO.read.color,
    severity: MODE_INFO.read.severity,
    detail: '',
  });
  /** Temporary mode owned by a modal or an inline action. */
  private readonly transientModeSignal = signal<OperationModeInfo | null>(null);
  private transientToken = 0;

  private readonly activeMode = computed(() => this.transientModeSignal() ?? this.pageModeSignal());

  readonly mode = computed(() => this.activeMode().mode);
  readonly detail = computed(() => this.activeMode().detail ?? '');
  readonly info = computed<OperationModeInfo>(() => this.activeMode());

  constructor() {
    this.router.events
      .pipe(
        filter((event): event is NavigationStart => event instanceof NavigationStart),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((event) => {
        const currentPath = this.router.url.split('?')[0];
        const targetPath = event.url.split('?')[0];
        // A query-param-only navigation (for example the single-hotel
        // prop_id injection) does not leave the page, so it must not close an
        // edit/delete/create overlay that belongs to that page.
        if (currentPath === targetPath) return;
        this.clearTransientMode();
      });

    this.router.events
      .pipe(
        filter((event): event is NavigationEnd => event instanceof NavigationEnd),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(() => this.syncPageModeFromRoute());

    // Covers the initial URL, before the first NavigationEnd is emitted.
    this.syncPageModeFromRoute();
  }

  /** Publish a temporary mode for a modal or inline operation. */
  setTransientMode(mode: OperationMode, detail = ''): () => void {
    const token = ++this.transientToken;
    this.transientModeSignal.set(this.toInfo(mode, detail));

    return () => {
      // A newer owner has taken over the single transient slot. Its cleanup
      // owns the slot now; an older effect must never restore stale UI state.
      if (this.transientToken !== token) return;
      this.transientModeSignal.set(null);
      this.transientToken += 1;
    };
  }

  /**
   * Backward-compatible alias for existing inline actions while they migrate
   * to the more explicit transient API.
   */
  setMode(mode: OperationMode, detail = ''): () => void {
    return this.setTransientMode(mode, detail);
  }

  /** Clear only the active transient mode; route metadata remains authoritative. */
  reset(): void {
    this.clearTransientMode();
  }

  private clearTransientMode(): void {
    this.transientToken += 1;
    this.transientModeSignal.set(null);
  }

  private syncPageModeFromRoute(): void {
    const routerState = this.router.routerState;
    if (!routerState?.snapshot?.root) return;
    let route = routerState.snapshot.root;
    while (route.firstChild) route = route.firstChild;
    const data = route.data as OperationModeRouteData;
    this.pageModeSignal.set(this.toInfo(data.operationMode ?? 'read', data.operationDetail ?? ''));
  }

  private toInfo(mode: OperationMode, detail: string): OperationModeInfo {
    return { mode, ...MODE_INFO[mode], detail };
  }
}
