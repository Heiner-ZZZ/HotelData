import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import { RoomTypeTableComponent } from '../../components/room-type-table/room-type-table';
import type { RoomsPageViewModel } from '../../models/rooms.model';
import { RoomsApiService } from '../../services/rooms-api.service';

@Component({
  selector: 'app-rooms-page',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    RoomTypeTableComponent
  ],
  templateUrl: './rooms-page.html',
  styleUrl: './rooms-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RoomsPageComponent {
  private readonly api = inject(RoomsApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<RoomsPageViewModel | null>(null);
  readonly feedback = signal<string>('');
  readonly errorMessage = signal<string>('');

  readonly filterForm = this.fb.nonNullable.group({
    propId: 0
  });

  readonly createForm = this.fb.nonNullable.group({
    name: ['', [Validators.required]],
    description: [''],
    maxAdults: [2, [Validators.required, Validators.min(1)]],
    maxChildren: [0, [Validators.required, Validators.min(0)]],
    baseCapacity: [2, [Validators.required, Validators.min(1)]],
    isActive: [true]
  });

  constructor() {
    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      const propId = Number(params.get('propId') ?? '0') || 0;
      this.load(propId);
    });
  }

  selectProperty() {
    const propId = this.filterForm.getRawValue().propId;
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { propId: propId || null }
    });
  }

  submitCreate() {
    const vm = this.viewModel();
    if (!vm || this.createForm.invalid) {
      this.createForm.markAllAsTouched();
      return;
    }

    this.feedback.set('');
    this.errorMessage.set('');
    const value = this.createForm.getRawValue();
    this.api
      .createRoomType(vm.property.propId, value)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.feedback.set('Tipo de habitacion registrado.');
          this.createForm.patchValue({
            name: '',
            description: '',
            maxAdults: 2,
            maxChildren: 0,
            baseCapacity: 2,
            isActive: true
          });
          this.load(vm.property.propId);
        },
        error: (error) => {
          this.errorMessage.set(error?.error?.detail || 'No fue posible guardar el tipo de habitacion.');
        }
      });
  }

  private load(initialPropId: number) {
    this.viewState.set('loading');
    this.feedback.set('');
    this.errorMessage.set('');
    this.api
      .getRooms(initialPropId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (vm) => {
          this.viewModel.set(vm);
          this.filterForm.patchValue({ propId: vm.selectedPropId || vm.property.propId }, { emitEvent: false });
          this.viewState.set(vm.roomTypes.length ? 'success' : 'empty');
        },
        error: () => {
          this.viewState.set('error');
        }
      });
  }
}
