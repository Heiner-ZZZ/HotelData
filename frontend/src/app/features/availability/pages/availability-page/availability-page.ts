import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, map, of, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { AvailabilityViewModel } from '../../models/availability.model';
import { AvailabilityApiService } from '../../services/availability-api.service';

@Component({
  selector: 'app-availability-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    PropertySelectorComponent,
    ReactiveFormsModule,
  ],
  templateUrl: './availability-page.html',
  styleUrl: './availability-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AvailabilityPageComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly api = inject(AvailabilityApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly router = inject(Router);

  readonly viewState = signal<ViewState>('loading');
  readonly pageData = signal<AvailabilityViewModel | null>(null);
  readonly errorMessage = signal('');
  readonly submitMessage = signal('');

  readonly selectedPropId = signal(0);
  readonly selectedLabel = signal('');

  readonly inventoryForm = this.formBuilder.nonNullable.group({
    roomTypeId: ['', [Validators.required]],
    date: ['', [Validators.required]],
    totalRooms: [0, [Validators.required, Validators.min(0)]],
    availableRooms: [0, [Validators.required, Validators.min(0)]],
    blockedRooms: [0, [Validators.required, Validators.min(0)]],
  });

  readonly blackoutForm = this.formBuilder.nonNullable.group({
    roomTypeId: ['', [Validators.required]],
    startDate: ['', [Validators.required]],
    endDate: ['', [Validators.required]],
    blockedRooms: [0, [Validators.required, Validators.min(0)]],
    reason: [''],
  });

  constructor() {
    this.activatedRoute.queryParamMap
      .pipe(
        map((params) => Number(params.get('prop_id') ?? '0')),
        distinctUntilChanged(),
        switchMap((propId) => {
          if (!propId) return of(null);
          this.viewState.set('loading');
          this.errorMessage.set('');
          this.submitMessage.set('');
          return this.api.getAvailability(propId);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (data) => {
          if (data) {
            this.pageData.set(data);
            this.selectedPropId.set(data.propId);
            this.selectedLabel.set(data.hotelName);
            this.viewState.set('success');
          }
        },
        error: () => {
          this.viewState.set('error');
          this.errorMessage.set('No se pudo cargar la información.');
        },
      });
  }

  onPropSelected(propId: number) {
    void this.router.navigate([], {
      relativeTo: this.activatedRoute,
      queryParams: { prop_id: propId || null },
    });
  }

  saveInventory(): void {
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
        blocked_rooms: this.inventoryForm.controls.blockedRooms.value,
      })
      .pipe(
        switchMap(() => this.api.getAvailability(propId)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (data) => {
          this.pageData.set(data);
          this.submitMessage.set('Inventario actualizado');
          this.errorMessage.set('');
          this.inventoryForm.reset({
            roomTypeId: '',
            date: '',
            totalRooms: 0,
            availableRooms: 0,
            blockedRooms: 0,
          });
        },
        error: (err: ApiError) => {
          this.errorMessage.set(err.message || 'Error al guardar inventario.');
          this.submitMessage.set('');
        },
      });
  }

  saveBlackout(): void {
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
        reason: this.blackoutForm.controls.reason.value,
      })
      .pipe(
        switchMap(() => this.api.getAvailability(propId)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (data) => {
          this.pageData.set(data);
          this.submitMessage.set('Bloqueo registrado');
          this.errorMessage.set('');
          this.blackoutForm.reset({
            roomTypeId: '',
            startDate: '',
            endDate: '',
            blockedRooms: 0,
            reason: '',
          });
        },
        error: (err: ApiError) => {
          this.errorMessage.set(err.message || 'Error al registrar bloqueo.');
          this.submitMessage.set('');
        },
      });
  }
}
