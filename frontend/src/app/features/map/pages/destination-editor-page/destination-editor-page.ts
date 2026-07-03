import { JsonPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { switchMap } from 'rxjs';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { ToastService } from '../../../../shared/services/toast.service';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { Destination } from '../../models/map.model';
import { MapApiService } from '../../services/map-api.service';
import { LocationPickerComponent } from '../../components/location-picker/location-picker';

@Component({
  selector: 'app-destination-editor-page',
  imports: [
    EmptyStateComponent, ErrorStateComponent, JsonPipe, LoadingStateComponent,
    PageHeaderComponent, ReactiveFormsModule, RouterLink, LocationPickerComponent,
  ],
  templateUrl: './destination-editor-page.html',
  styleUrl: './destination-editor-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DestinationEditorPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(MapApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly toast = inject(ToastService);

  readonly viewState = signal<ViewState>('loading');
  readonly destination = signal<Destination | null>(null);
  readonly saved = signal(false);
  readonly errorMessage = signal('');
  readonly destinationId = signal(0);

  readonly editForm = this.formBuilder.nonNullable.group({
    visibleName: ['', Validators.required],
    country: [''],
    city: [''],
    description: [''],
    latitude: [0],
    longitude: [0],
  });

  constructor() {
    this.route.paramMap.pipe(
      switchMap((params) => {
        const id = Number(params.get('id'));
        this.destinationId.set(id);
        this.viewState.set('loading');
        return this.api.getDestination(id);
      }),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (dest) => {
        this.destination.set(dest);
        this.editForm.patchValue({
          visibleName: dest.visibleName || dest.destinationDisplayName,
          country: dest.country,
          city: dest.city,
          description: dest.description,
          latitude: dest.latitude ?? undefined,
          longitude: dest.longitude ?? undefined,
        });
        this.viewState.set('success');
      },
      error: () => this.viewState.set('error'),
    });
  }

  onLocationChange(coords: { latitude: number; longitude: number }) {
    this.editForm.patchValue({
      latitude: coords.latitude,
      longitude: coords.longitude,
    });
  }

  handleRetry() {
    void this.router.navigate(['/admin/destinations']);
  }

  save() {
    if (this.editForm.invalid) return;
    const val = this.editForm.getRawValue();
    this.saved.set(false);
    this.errorMessage.set('');

    this.api.updateDestination(this.destinationId(), {
      visible_name: val.visibleName,
      country: val.country || undefined,
      city: val.city || undefined,
      description: val.description || undefined,
      latitude: val.latitude || null,
      longitude: val.longitude || null,
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (updated) => {
        this.destination.set(updated);
        this.saved.set(true);
        this.toast.show('Destino actualizado correctamente.', 'info', 4000);
      },
      error: (err) => {
        this.errorMessage.set(err.message || 'Error al guardar el destino.');
      },
    });
  }
}
