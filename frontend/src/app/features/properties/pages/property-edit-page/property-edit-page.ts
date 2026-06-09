import { ChangeDetectionStrategy, Component, DestroyRef, inject, isDevMode, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { filter, map, switchMap } from 'rxjs';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { EditPropertyViewModel } from '../../models/properties.model';
import { PropertiesApiService } from '../../services/properties-api.service';

@Component({
  selector: 'app-property-edit-page',
  imports: [ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, ReactiveFormsModule],
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
  readonly newImageUrl = signal('');
  readonly newImageTitle = signal('');

  readonly form = this.fb.nonNullable.group({
    hotelName: ['', Validators.required],
    displayName: ['', Validators.required],
    displayCountryLabel: [''],
    description: ['', Validators.required],
    checkInTime: [''],
    checkOutTime: [''],
    cancellationPolicy: [''],
    petPolicy: [false]
  });

  readonly propId = signal(0);

  constructor() {
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
            checkInTime: vm.policies.checkInTime,
            checkOutTime: vm.policies.checkOutTime,
            cancellationPolicy: vm.policies.cancellationPolicy,
            petPolicy: vm.policies.petPolicy === 'true' || vm.policies.petPolicy === 'yes'
          });
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
          manualOverride: true,
          profileBadge: 'Nombre editado manualmente'
        });
        this.saving.set('done');
        setTimeout(() => this.saving.set('idle'), 3000);
      } else {
        this.saveError.set('Error al guardar algunos cambios');
        this.saving.set('idle');
      }
    });
  }

  focusImageInput() {
    const el = document.getElementById('imageUrlInput');
    el?.focus();
  }

  discard() {
    const currentVm = this.vm();
    if (!currentVm) return;
    this.form.patchValue({
      hotelName: currentVm.hotelName,
      displayName: currentVm.displayName,
      displayCountryLabel: currentVm.countryDisplayName,
      description: currentVm.description,
      checkInTime: currentVm.policies.checkInTime,
      checkOutTime: currentVm.policies.checkOutTime,
      cancellationPolicy: currentVm.policies.cancellationPolicy,
      petPolicy: currentVm.policies.petPolicy === 'true'
    });
    this.saving.set('idle');
    this.saveError.set('');
  }

  removeAmenity(label: string) {
    const current = this.vm();
    if (!current) return;
    this.vm.set({ ...current, amenities: current.amenities.filter(a => a !== label) });
  }

  addImage() {
    const url = this.newImageUrl().trim();
    if (!url) return;
    const current = this.vm();
    if (!current) return;
    const title = this.newImageTitle().trim();
    this.propertiesApi.addImage(this.propId(), url, title).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.vm.set({ ...current, images: [...current.images, { imageUrl: url, title }] });
        this.newImageUrl.set('');
        this.newImageTitle.set('');
      }
    });
  }

  removeImage(imageUrl: string) {
    const current = this.vm();
    if (!current) return;
    this.propertiesApi.deleteImage(this.propId(), imageUrl).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.vm.set({ ...current, images: current.images.filter(i => i.imageUrl !== imageUrl) });
      }
    });
  }

  onImageUrlInput(event: Event) {
    this.newImageUrl.set((event.target as HTMLInputElement).value);
  }

  onImageTitleInput(event: Event) {
    this.newImageTitle.set((event.target as HTMLInputElement).value);
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
    if (fv.checkInTime !== current.policies.checkInTime) count++;
    if (fv.checkOutTime !== current.policies.checkOutTime) count++;
    if (fv.cancellationPolicy !== current.policies.cancellationPolicy) count++;
    if (fv.petPolicy !== (current.policies.petPolicy === 'true')) count++;
    return count;
  }
}
