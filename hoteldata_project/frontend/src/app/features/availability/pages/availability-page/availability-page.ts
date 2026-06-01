import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, forkJoin, map, of, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { AvailabilityPropertyOption, AvailabilityViewModel } from '../../models/availability.model';
import { AvailabilityApiService } from '../../services/availability-api.service';

@Component({
  selector: 'app-availability-page',
  imports: [EmptyStateComponent, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, ReactiveFormsModule],
  templateUrl: './availability-page.html',
  styleUrl: './availability-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AvailabilityPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly api = inject(AvailabilityApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly pageData = signal<AvailabilityViewModel | null>(null);
  readonly propertyOptions = signal<AvailabilityPropertyOption[]>([]);
  readonly errorMessage = signal('');
  readonly submitMessage = signal('');

  readonly selectedPropId = computed(() => this.pageData()?.propId ?? 0);

  readonly selectorForm = this.formBuilder.nonNullable.group({
    propId: [0, [Validators.required, Validators.min(1)]]
  });

  readonly inventoryForm = this.formBuilder.nonNullable.group({
    roomTypeId: ['', [Validators.required]],
    date: ['', [Validators.required]],
    totalRooms: [0, [Validators.required, Validators.min(0)]],
    availableRooms: [0, [Validators.required, Validators.min(0)]],
    blockedRooms: [0, [Validators.required, Validators.min(0)]]
  });

  readonly blackoutForm = this.formBuilder.nonNullable.group({
    roomTypeId: ['', [Validators.required]],
    startDate: ['', [Validators.required]],
    endDate: ['', [Validators.required]],
    blockedRooms: [0, [Validators.required, Validators.min(0)]],
    reason: ['']
  });

  constructor() {
    this.activatedRoute.queryParamMap
      .pipe(
        map((params) => Number(params.get('prop_id') ?? '0')),
        distinctUntilChanged(),
        switchMap((propId) => {
          this.viewState.set('loading');
          this.errorMessage.set('');
          this.submitMessage.set('');

          return forkJoin({
            options: this.api.getPropertyOptions(),
            availability: propId > 0 ? this.api.getAvailability(propId) : of(null)
          });
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: ({ options, availability }) => {
          this.propertyOptions.set(options);
          if (!this.selectorForm.controls.propId.value && options.length) {
            this.selectorForm.controls.propId.setValue(options[0].propId);
          }
          if (availability) {
            this.pageData.set(availability);
            this.selectorForm.controls.propId.setValue(availability.propId, { emitEvent: false });
            this.viewState.set('success');
          } else {
            this.pageData.set(null);
            this.viewState.set(options.length ? 'empty' : 'success');
          }
        },
        error: () => this.viewState.set('error')
      });
  }

  selectProperty() {
    const propId = this.selectorForm.controls.propId.value;
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { prop_id: propId || null }
    });
  }

  saveInventory() {
    const propId = this.selectedPropId();
    if (!propId || this.inventoryForm.invalid) {
      this.inventoryForm.markAllAsTouched();
      return;
    }

    this.api
      .saveInventory({
        prop_id: propId,
        room_type_id: this.inventoryForm.controls.roomTypeId.value,
        date: this.inventoryForm.controls.date.value,
        total_rooms: this.inventoryForm.controls.totalRooms.value,
        available_rooms: this.inventoryForm.controls.availableRooms.value,
        blocked_rooms: this.inventoryForm.controls.blockedRooms.value
      })
      .pipe(
        switchMap(() => this.api.getAvailability(propId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (availability) => {
          this.pageData.set(availability);
          this.submitMessage.set('Inventario actualizado');
          this.errorMessage.set('');
          this.inventoryForm.reset({
            roomTypeId: '',
            date: '',
            totalRooms: 0,
            availableRooms: 0,
            blockedRooms: 0
          });
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible guardar el inventario.');
          this.submitMessage.set('');
        }
      });
  }

  saveBlackout() {
    const propId = this.selectedPropId();
    if (!propId || this.blackoutForm.invalid) {
      this.blackoutForm.markAllAsTouched();
      return;
    }

    this.api
      .createBlackout({
        prop_id: propId,
        room_type_id: this.blackoutForm.controls.roomTypeId.value,
        start_date: this.blackoutForm.controls.startDate.value,
        end_date: this.blackoutForm.controls.endDate.value,
        blocked_rooms: this.blackoutForm.controls.blockedRooms.value,
        reason: this.blackoutForm.controls.reason.value
      })
      .pipe(
        switchMap(() => this.api.getAvailability(propId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (availability) => {
          this.pageData.set(availability);
          this.submitMessage.set('Bloqueo registrado');
          this.errorMessage.set('');
          this.blackoutForm.reset({
            roomTypeId: '',
            startDate: '',
            endDate: '',
            blockedRooms: 0,
            reason: ''
          });
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible registrar el bloqueo.');
          this.submitMessage.set('');
        }
      });
  }
}
