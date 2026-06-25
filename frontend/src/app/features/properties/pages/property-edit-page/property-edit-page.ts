import { ChangeDetectionStrategy, Component, DestroyRef, inject, isDevMode, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { filter, map, switchMap } from 'rxjs';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { ImageGalleryComponent } from './components/image-gallery';
import { AmenitiesPanelComponent } from './components/amenities-panel';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { EditPropertyViewModel } from '../../models/properties.model';
import { PropertiesApiService } from '../../services/properties-api.service';

@Component({
  selector: 'app-property-edit-page',
  imports: [ErrorStateComponent, ImageGalleryComponent, AmenitiesPanelComponent, LoadingStateComponent, PageHeaderComponent, ReactiveFormsModule],
  templateUrl: './property-edit-page.html',
  styleUrl: './property-edit-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PropertyEditPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly propertiesApi = inject(PropertiesApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly fb = inject(FormBuilder);

  readonly viewState = signal<ViewState>('loading');
  readonly saving = signal<'idle' | 'saving' | 'done'>('idle');
  readonly saveError = signal('');
  readonly vm = signal<EditPropertyViewModel | null>(null);
  readonly hasUnsavedChanges = signal(false);
  private readonly formInitialized = signal(false);

  readonly form = this.fb.nonNullable.group({
    hotelName: ['', Validators.required],
    displayName: ['', Validators.required],
    displayCountryLabel: [''],
    description: ['', Validators.required],
    highlights: [''],
    checkInTime: [''],
    checkOutTime: [''],
    cancellationPolicy: [''],
    petPolicy: [false]
  });

  readonly propId = signal(0);

  constructor() {
    // Track form changes for the save bar (zoneless-safe signal)
    this.form.valueChanges
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        filter(() => this.formInitialized())
      )
      .subscribe(() => {
        this.hasUnsavedChanges.set(this.unsavedCount() > 0);
      });

    this.route.paramMap
      .pipe(
        map((params) => Number(params.get('propertyId'))),
        filter((propId) => Number.isFinite(propId) && propId > 0),
        switchMap((propId) => {
          this.propId.set(propId);
          this.viewState.set('loading');
          if (isDevMode()) {
            console.log('Loading property profile endpoint', propId);
          }
          return this.propertiesApi.loadPropertyProfile(propId);
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (vm) => {
          this.vm.set(vm);
          this.form.patchValue({
            hotelName: vm.hotelName,
            displayName: vm.displayName,
            displayCountryLabel: vm.countryDisplayName,
            description: vm.description,
            highlights: vm.highlights,
            checkInTime: vm.policies.checkInTime,
            checkOutTime: vm.policies.checkOutTime,
            cancellationPolicy: vm.policies.cancellationPolicy,
            petPolicy: vm.policies.petPolicy === 'true' || vm.policies.petPolicy === 'yes'
          });
          this.formInitialized.set(true);
          this.viewState.set('success');
        },
        error: (error) => {
          if (isDevMode()) {
            console.error('Error loading property profile', error);
          }
          this.viewState.set('error');
        }
      });
  }

  saveAll() {
    const currentVm = this.vm();
    if (!currentVm) return;
    this.saving.set('saving');
    this.saveError.set('');

    const fv = this.form.getRawValue();
    const propId = this.propId();
    const checks: Promise<boolean>[] = [];

    checks.push(
      this.propertiesApi
        .saveProfile(propId, {
          hotel_name: fv.hotelName,
          display_name: fv.displayName,
          description: fv.description,
          display_country_label: fv.displayCountryLabel,
          reason: 'Actualización manual desde Angular'
        })
        .toPromise()
        .then(() => true)
        .catch(() => false)
    );

    // RF-005: Save content (description + highlights)
    checks.push(
      this.propertiesApi.saveContent(propId, fv.description, fv.highlights)
        .toPromise()
        .then(() => true)
        .catch(() => false)
    );

    checks.push(this.propertiesApi.savePolicies(propId, {
      check_in_time: fv.checkInTime,
      check_out_time: fv.checkOutTime,
      cancellation_policy: fv.cancellationPolicy,
      pet_policy: fv.petPolicy ? 'true' : 'false',
      children_policy: currentVm.policies.childrenPolicy,
      extra_bed_policy: currentVm.policies.extraBedPolicy,
      payment_policy: currentVm.policies.paymentPolicy,
      house_rules: currentVm.policies.houseRules,
    }).toPromise().then(() => true).catch(() => false));

    checks.push(this.propertiesApi.saveAmenities(propId, currentVm.amenities).toPromise().then(() => true).catch(() => false));

    Promise.all(checks).then((results) => {
      if (results.every(r => r)) {
        this.vm.set({
          ...currentVm,
          hotelName: fv.hotelName,
          displayName: fv.displayName,
          countryDisplayName: fv.displayCountryLabel,
          description: fv.description,
          highlights: fv.highlights ?? '',
          manualOverride: true,
          profileBadge: 'Nombre editado manualmente'
        });
        this.saving.set('done');
        this.hasUnsavedChanges.set(false);
        setTimeout(() => this.saving.set('idle'), 3000);
      } else {
        this.saveError.set('Error al guardar algunos cambios');
        this.saving.set('idle');
      }
    });
  }

  discard() {
    const currentVm = this.vm();
    if (!currentVm) return;
    this.form.patchValue({
      hotelName: currentVm.hotelName,
      displayName: currentVm.displayName,
      displayCountryLabel: currentVm.countryDisplayName,
      description: currentVm.description,
      highlights: currentVm.highlights,
      checkInTime: currentVm.policies.checkInTime,
      checkOutTime: currentVm.policies.checkOutTime,
      cancellationPolicy: currentVm.policies.cancellationPolicy,
      petPolicy: currentVm.policies.petPolicy === 'true'
    });
    this.saving.set('idle');
    this.saveError.set('');
  }

  onAmenityChange(amenities: string[]) {
    const current = this.vm();
    if (current) {
      this.vm.set({ ...current, amenities });
    }
  }

  onImagesChange(images: { imageUrl: string; title: string }[]) {
    const current = this.vm();
    if (current) {
      this.vm.set({ ...current, images });
    }
  }

  onGalleryError(msg: string) {
    this.saveError.set(msg);
  }

  unsavedCount(): number {
    const current = this.vm();
    if (!current) return 0;
    const fv = this.form.getRawValue();
    let count = 0;
    if (fv.hotelName !== current.hotelName) count++;
    if (fv.displayName !== current.displayName) count++;
    if (fv.displayCountryLabel !== current.countryDisplayName) count++;
    if (fv.description !== current.description) count++;
    if ((fv.highlights ?? '') !== (current.highlights ?? '')) count++;
    if (fv.checkInTime !== current.policies.checkInTime) count++;
    if (fv.checkOutTime !== current.policies.checkOutTime) count++;
    if (fv.cancellationPolicy !== current.policies.cancellationPolicy) count++;
    if (fv.petPolicy !== (current.policies.petPolicy === 'true')) count++;
    return count;
  }
}
