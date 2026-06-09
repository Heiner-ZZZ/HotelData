import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { distinctUntilChanged, forkJoin, map, of, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { RoomPropertyOption, RoomsViewModel } from '../../models/rooms.model';
import { RoomsApiService } from '../../services/rooms-api.service';
import { RoomTypeTableComponent } from '../../components/room-type-table/room-type-table';

@Component({
  selector: 'app-rooms-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
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
  readonly propertyOptions = signal<RoomPropertyOption[]>([]);
  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly selectorForm = this.formBuilder.nonNullable.group({
    propId: [0, [Validators.required, Validators.min(1)]]
  });

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
          return forkJoin({
            options: this.api.getOptions(),
            rooms: propId > 0 ? this.api.getRooms(propId) : of(null)
          });
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: ({ options, rooms }) => {
          this.propertyOptions.set(options);
          if (!this.selectorForm.controls.propId.value && options.length) {
            this.selectorForm.controls.propId.setValue(options[0].propId);
          }
          if (rooms) {
            this.viewModel.set(rooms);
            this.selectorForm.controls.propId.setValue(rooms.propId, { emitEvent: false });
            this.viewState.set('success');
          } else {
            this.viewModel.set(null);
            this.viewState.set(options.length ? 'empty' : 'success');
          }
        },
        error: () => this.viewState.set('error')
      });
  }

  selectProperty() {
    const propId = this.selectorForm.controls.propId.value;
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
