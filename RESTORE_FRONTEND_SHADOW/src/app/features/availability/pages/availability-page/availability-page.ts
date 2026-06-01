import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { AvailabilityCalendarComponent } from '../../components/availability-calendar/availability-calendar';
import { AvailabilityToolbarComponent } from '../../components/availability-toolbar/availability-toolbar';
import { BulkEditPanelComponent } from '../../components/bulk-edit-panel/bulk-edit-panel';
import { UnsavedChangesBannerComponent } from '../../components/unsaved-changes-banner/unsaved-changes-banner';
import type {
  AvailabilityBulkEdit,
  AvailabilityCellChange,
  AvailabilityRow,
  AvailabilitySnapshot,
} from '../../models/availability.model';
import { AvailabilityApiService } from '../../services/availability-api.service';

@Component({
  selector: 'app-availability-page',
  standalone: true,
  imports: [
    AvailabilityCalendarComponent,
    AvailabilityToolbarComponent,
    BulkEditPanelComponent,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    ReactiveFormsModule,
    UnsavedChangesBannerComponent,
  ],
  templateUrl: './availability-page.html',
  styleUrl: './availability-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AvailabilityPageComponent {
  private readonly api = inject(AvailabilityApiService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  readonly viewState = signal<ViewState>('loading');
  readonly saveState = signal<'idle' | 'saving' | 'error'>('idle');
  readonly snapshot = signal<AvailabilitySnapshot | null>(null);
  readonly rows = signal<AvailabilityRow[]>([]);
  readonly originalRows = signal<AvailabilityRow[]>([]);
  readonly saveError = signal('');

  readonly filtersForm = this.formBuilder.nonNullable.group({
    propId: [''],
    roomTypeId: [''],
    ratePlanId: [''],
    startDate: [this.defaultDate(0)],
    endDate: [this.defaultDate(13)],
  });

  readonly rowErrors = computed(() => {
    const errors: Record<string, string | null> = {};
    for (const row of this.rows()) {
      errors[row.date] = this.validateRow(row);
    }
    return errors;
  });

  readonly dirtyDates = computed(() => {
    const dirty = new Set<string>();
    const originalMap = new Map(this.originalRows().map((item) => [item.date, item]));
    for (const row of this.rows()) {
      const original = originalMap.get(row.date);
      if (!original || JSON.stringify(original) !== JSON.stringify(row)) {
        dirty.add(row.date);
      }
    }
    return dirty;
  });

  readonly dirtyRows = computed(() => {
    const dirty = this.dirtyDates();
    return this.rows().filter((row) => dirty.has(row.date));
  });

  readonly hasValidationErrors = computed(() =>
    this.dirtyRows().some((row) => !!this.rowErrors()[row.date]),
  );

  constructor() {
    this.loadAvailability();
  }

  reloadAvailability() {
    this.loadAvailability();
  }

  onCellChanged(change: AvailabilityCellChange) {
    this.rows.update((current) =>
      current.map((row) =>
        row.date === change.date
          ? {
              ...row,
              [change.field]: change.value,
            }
          : row,
      ),
    );
  }

  onBulkApply(patch: AvailabilityBulkEdit) {
    this.rows.update((current) =>
      current.map((row) => {
        if (row.date < patch.startDate || row.date > patch.endDate) {
          return row;
        }
        return {
          ...row,
          totalRooms: patch.totalRooms ?? row.totalRooms,
          availableRooms: patch.availableRooms ?? row.availableRooms,
          blockedRooms: patch.blockedRooms ?? row.blockedRooms,
          rateAmount: patch.rateAmount ?? row.rateAmount,
          minStayNights: patch.minStayNights ?? row.minStayNights,
          isClosed:
            patch.closedMode === 'keep'
              ? row.isClosed
              : patch.closedMode === 'closed',
        };
      }),
    );
  }

  discardChanges() {
    this.rows.set(this.cloneRows(this.originalRows()));
    this.saveState.set('idle');
    this.saveError.set('');
  }

  saveChanges() {
    const currentSnapshot = this.snapshot();
    const roomTypeId = currentSnapshot?.filters.roomTypeId;
    if (!currentSnapshot || !roomTypeId || !this.dirtyRows().length || this.hasValidationErrors()) {
      return;
    }

    this.saveState.set('saving');
    this.saveError.set('');
    this.api
      .saveUpdates({
        propId: currentSnapshot.filters.propId,
        roomTypeId,
        ratePlanId: currentSnapshot.filters.ratePlanId,
        rows: this.dirtyRows(),
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.saveState.set('idle');
          this.loadAvailability();
        },
        error: (error: { message?: string }) => {
          this.saveState.set('error');
          this.saveError.set(error.message || 'No se pudieron guardar los cambios.');
        },
      });
  }

  private loadAvailability() {
    this.viewState.set('loading');
    const raw = this.filtersForm.getRawValue();
    const propId = Number(raw.propId);

    const filters = {
      propId: propId || 0,
      roomTypeId: raw.roomTypeId || null,
      ratePlanId: raw.ratePlanId || null,
      startDate: raw.startDate,
      endDate: raw.endDate,
    };

    if (!filters.propId) {
      this.api
        .getOptions()
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe({
          next: (dto: any) => {
            const firstProp = dto.selected_prop_id || dto.property_options?.[0]?.prop_id;
            if (!firstProp) {
              this.snapshot.set(null);
              this.rows.set([]);
              this.originalRows.set([]);
              this.viewState.set('empty');
              return;
            }
            this.filtersForm.patchValue({ propId: String(firstProp) }, { emitEvent: false });
            this.loadAvailability();
          },
          error: () => this.viewState.set('error'),
        });
        return;
    }

    this.api
      .getSnapshot(filters)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (snapshot) => {
          this.snapshot.set(snapshot);
          this.rows.set(this.cloneRows(snapshot.rows));
          this.originalRows.set(this.cloneRows(snapshot.rows));
          this.filtersForm.patchValue(
            {
              propId: String(snapshot.filters.propId),
              roomTypeId: snapshot.filters.roomTypeId ?? '',
              ratePlanId: snapshot.filters.ratePlanId ?? '',
              startDate: snapshot.filters.startDate,
              endDate: snapshot.filters.endDate,
            },
            { emitEvent: false },
          );
          this.viewState.set(snapshot.rows.length ? 'success' : 'empty');
        },
        error: () => this.viewState.set('error'),
      });
  }

  private validateRow(row: AvailabilityRow) {
    const total = row.totalRooms ?? 0;
    const available = row.availableRooms ?? 0;
    const blocked = row.blockedRooms ?? 0;
    const minStay = row.minStayNights ?? 1;
    const rate = row.rateAmount;

    if (total < 0 || available < 0 || blocked < 0) {
      return 'Inventario negativo no permitido.';
    }
    if (available > total) {
      return 'Disponibles no puede superar el total.';
    }
    if (blocked > total) {
      return 'Bloqueadas no puede superar el total.';
    }
    if (available + blocked > total) {
      return 'Disponibles + bloqueadas no puede superar el total.';
    }
    if (rate !== null && rate < 0) {
      return 'La tarifa no puede ser negativa.';
    }
    if (minStay < 1) {
      return 'El minimo de noches debe ser al menos 1.';
    }
    return null;
  }

  private cloneRows(rows: AvailabilityRow[]) {
    return rows.map((row) => ({ ...row }));
  }

  private defaultDate(offset: number) {
    const current = new Date();
    current.setDate(current.getDate() + offset);
    return current.toISOString().slice(0, 10);
  }
}
