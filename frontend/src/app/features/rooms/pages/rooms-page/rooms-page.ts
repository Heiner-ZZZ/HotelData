import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, map, of, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { RoomsViewModel } from '../../models/rooms.model';
import { RoomsApiService } from '../../services/rooms-api.service';
import { RoomTypeTableComponent } from '../../components/room-type-table/room-type-table';

@Component({
  selector: 'app-rooms-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    PropertySelectorComponent,
    ReactiveFormsModule,
    RoomTypeTableComponent,
    RouterLink
  ],
  templateUrl: './rooms-page.html',
  styleUrl: './rooms-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RoomsPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(RoomsApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<RoomsViewModel | null>(null);
  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly selectedPropId = signal(0);
  readonly selectedLabel = signal('');

  readonly createForm = this.formBuilder.nonNullable.group({
    name: ['', [Validators.required]],
    description: [''],
    maxAdults: [2, [Validators.required, Validators.min(1)]],
    maxChildren: [0, [Validators.required, Validators.min(0)]],
    baseCapacity: [2, [Validators.required, Validators.min(1)]],
    isActive: [true]
  });

  constructor() {
    this.route.queryParamMap
      .pipe(
        map((params) => Number(params.get('prop_id') ?? '0')),
        distinctUntilChanged(),
        switchMap((propId) => {
          this.viewState.set('loading');
          this.message.set('');
          this.errorMessage.set('');
          return propId > 0 ? this.api.getRooms(propId) : of(null);
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (rooms) => {
          if (rooms) {
            this.viewModel.set(rooms);
            this.selectedPropId.set(rooms.propId);
            this.selectedLabel.set(rooms.hotelName);
            this.viewState.set('success');
          } else {
            this.viewModel.set(null);
            this.viewState.set('empty');
          }
        },
        error: () => this.viewState.set('error')
      });
  }

  onPropSelected(propId: number) {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: propId || null }
    });
  }

  createRoomType() {
    const current = this.viewModel();
    if (!current || this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      return;
    }

    const value = this.createForm.getRawValue();
    this.api
      .createRoomType({
        propId: current.propId,
        name: value.name,
        description: value.description,
        maxAdults: value.maxAdults,
        maxChildren: value.maxChildren,
        baseCapacity: value.baseCapacity,
        isActive: value.isActive
      })
      .pipe(
        switchMap(() => this.api.getRooms(current.propId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (rooms) => {
          this.viewModel.set(rooms);
          this.message.set('Tipo de habitación registrado');
          this.errorMessage.set('');
          this.createForm.reset({
            name: '',
            description: '',
            maxAdults: 2,
            maxChildren: 0,
            baseCapacity: 2,
            isActive: true
          });
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible registrar el tipo de habitación.');
          this.message.set('');
        }
      });
  }
}
