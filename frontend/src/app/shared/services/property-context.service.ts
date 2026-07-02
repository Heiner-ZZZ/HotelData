import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { inject, Injectable, signal } from '@angular/core';
import { catchError, map, of, shareReplay } from 'rxjs';

import { API_CONFIG } from '../../core/api/api.config';

export interface PropertyContextDto {
  mode: string;
  assigned_properties: Array<{ prop_id: number; label: string }>;
  default_prop_id: number;
}

@Injectable({ providedIn: 'root' })
export class PropertyContextService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  readonly currentPropId = signal(0);
  readonly currentPropLabel = signal('');
  readonly currentPropLabelShort = signal('');

  /** The property access mode for the current user. */
  readonly mode = signal<'all' | 'single' | 'multi' | 'none'>('all');
  /** Assigned properties (only populated in single/multi mode). */
  readonly assignedProperties = signal<Array<{ propId: number; label: string }>>([]);
  /** True when the context has been loaded from the backend. */
  readonly ready = signal(false);

  /** Whether the current user has a single-hotel restriction (mode=single). */
  readonly singleHotelMode = signal(false);

  constructor() {
    this.http
      .get<PropertyContextDto>(`${this.apiConfig.baseUrl}/management/properties/context`, {
        withCredentials: true,
      })
      .pipe(
        map((dto) => ({
          mode: dto.mode as 'all' | 'single' | 'multi' | 'none',
          assignedProperties: dto.assigned_properties.map((p) => ({
            propId: p.prop_id,
            label: p.label,
          })),
          defaultPropId: dto.default_prop_id,
        })),
        catchError((err: unknown) => {
          // Si hay error (red, auth, etc.), mantener modo 'all' como fallback seguro
          // para que el selector siga funcionando con la experiencia normal.
          console.warn('[PropertyContext] Error cargando contexto, usando fallback all:', err instanceof HttpErrorResponse ? err.status : err);
          return of({
            mode: 'all' as const,
            assignedProperties: [] as Array<{ propId: number; label: string }>,
            defaultPropId: 0,
          });
        }),
        shareReplay(1),
      )
      .subscribe((ctx) => {
        this.mode.set(ctx.mode);
        this.assignedProperties.set(ctx.assignedProperties);
        this.singleHotelMode.set(ctx.mode === 'single');

        if (ctx.mode === 'single' && ctx.defaultPropId) {
          const prop = ctx.assignedProperties.find((p) => p.propId === ctx.defaultPropId);
          if (prop) {
            this.setProperty(prop.propId, prop.label);
          }
        }

        this.ready.set(true);
      });
  }

  setProperty(propId: number, label: string): void {
    this.currentPropId.set(propId);
    this.currentPropLabel.set(label);
    const short = label.length > 18 ? label.slice(0, 16) + '\u2026' : label;
    this.currentPropLabelShort.set(short);
  }

  clear(): void {
    this.currentPropId.set(0);
    this.currentPropLabel.set('');
    this.currentPropLabelShort.set('');
  }
}
