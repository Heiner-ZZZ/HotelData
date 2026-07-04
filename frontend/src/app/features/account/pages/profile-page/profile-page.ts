import { DatePipe } from '@angular/common';
import { HttpEventType } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  HostListener,
  inject,
  signal,
  viewChild,
  ViewEncapsulation,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import type { ApiError } from '../../../../core/api/api-error.model';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { ProfileSecurityComponent } from './components/profile-security';
import { PpHeroComponent } from './partials/pp-hero';
import { PpTabBarComponent } from './partials/pp-tab-bar';
import { PpPersonalFormComponent } from './partials/pp-personal-form';
import { PpAvatarSectionComponent } from './partials/pp-avatar-section';
import { PpTravelSectionComponent } from './partials/pp-travel-section';
import type { ProfileViewModel } from '../../models/profile.model';
import type { SelectOption } from '../../models/profile.model';
import {
  DOCUMENT_TYPES,
  LANGUAGE_OPTIONS,
  TRAVEL_ACCOMMODATION_OPTIONS,
  TRAVEL_BUDGET_OPTIONS,
  TRAVEL_COMPANIONS_OPTIONS,
  TRAVEL_DESTINATION_OPTIONS,
  TRAVEL_PURPOSE_OPTIONS,
} from '../../models/profile.model';
import type { AvatarUploadResponse } from '../../services/profile-api.service';
import { ProfileApiService } from '../../services/profile-api.service';

@Component({
  selector: 'app-profile-page',
  imports: [DatePipe, ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, ProfileSecurityComponent, ReactiveFormsModule,
    PpHeroComponent, PpTabBarComponent, PpPersonalFormComponent,
    PpAvatarSectionComponent, PpTravelSectionComponent],
  templateUrl: './profile-page.html',
  styleUrl: './profile-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
})
export class ProfilePageComponent {
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly profileApi = inject(ProfileApiService);

  protected readonly Math = Math;

  readonly fileInput = viewChild<ElementRef<HTMLInputElement>>('fileInput');

  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly uploading = signal(false);
  readonly uploadProgress = signal(0);
  readonly successMessage = signal('');
  readonly errorMessage = signal('');
  readonly profile = signal<ProfileViewModel | null>(null);
  readonly previewUrl = signal<string | null>(null);
  readonly dragOver = signal(false);
  readonly activeTab = signal<'personal' | 'contact' | 'preferences' | 'social'>('personal');

  readonly tabs = [
    { key: 'personal' as const, label: 'Personal', icon: 'badge' },
    { key: 'contact' as const, label: 'Contacto', icon: 'contact_mail' },
    { key: 'social' as const, label: 'Redes y viajes', icon: 'travel_explore' },
    { key: 'preferences' as const, label: 'Preferencias', icon: 'settings' },
  ];

  readonly languageOptions = LANGUAGE_OPTIONS;
  readonly documentTypes = DOCUMENT_TYPES;
  readonly travelPurposeOptions = TRAVEL_PURPOSE_OPTIONS;
  readonly travelBudgetOptions = TRAVEL_BUDGET_OPTIONS;
  readonly travelCompanionsOptions = TRAVEL_COMPANIONS_OPTIONS;
  readonly travelAccommodationOptions = TRAVEL_ACCOMMODATION_OPTIONS;
  readonly travelDestinationOptions = TRAVEL_DESTINATION_OPTIONS;

  readonly form = this.formBuilder.nonNullable.group({
    // Personal
    displayName: ['', Validators.required],
    dateOfBirth: [''],
    nationality: [''],
    idDocumentType: [''],
    idDocumentNumber: [''],
    // Contact
    phone: [''],
    notificationEmail: ['', Validators.email],
    addressStreet: [''],
    addressCity: [''],
    addressState: [''],
    addressCountry: [''],
    addressPostalCode: [''],
    // Preferences
    preferredLanguage: ['es'],
    marketingOptIn: [false],
    notificationEmailEnabled: [true],
    notificationSmsEnabled: [false],
    // Avatar
    avatarUrl: [''],
    // Social media
    socialInstagram: [''],
    socialFacebook: [''],
    socialTwitter: [''],
    socialLinkedin: [''],
    // Travel preferences
    travelPurpose: [''],
    travelBudget: [''],
    travelCompanions: [''],
    travelAccommodation: [''],
    travelDestinationType: [''],
    travelInterests: [''],
    travelFrequentFlyer: [''],
    travelLoyaltyPrograms: [''],
    travelNotes: [''],
  });

  readonly activeDropdown = signal<string | null>(null);
  private readonly dropdownElements = new Map<string, HTMLElement>();

  registerDropdown(key: string, el: HTMLElement): void {
    this.dropdownElements.set(key, el);
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    const activeKey = this.activeDropdown();
    if (!activeKey) return;

    const el = this.dropdownElements.get(activeKey);
    if (el && !el.contains(event.target as Node)) {
      this.activeDropdown.set(null);
    }
  }

  toggleDropdown(key: string): void {
    this.activeDropdown.update(v => (v === key ? null : key));
  }

  selectOption(controlName: string, value: string): void {
    this.form.patchValue({ [controlName]: value });
    this.activeDropdown.set(null);
  }

  getSelectedLabel(options: SelectOption[], value: string): string {
    return options.find(o => o.value === value)?.label || 'Seleccionar…';
  }

  getSelectedIcon(options: SelectOption[], value: string): string | undefined {
    if (!value) return undefined;
    return options.find(o => o.value === value)?.icon;
  }

  constructor() {
    this.loadProfile();
  }

  private loadProfile(): void {
    this.loading.set(true);
    this.profileApi
      .getProfile()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (profile: ProfileViewModel) => {
          this.profile.set(profile);
          this.patchForm(profile);
          this.loading.set(false);
        },
        error: () => {
          this.errorMessage.set('No fue posible cargar tu perfil.');
          this.loading.set(false);
        },
      });
  }

  private patchForm(profile: ProfileViewModel): void {
    this.form.patchValue({
      displayName: profile.displayName,
      dateOfBirth: profile.dateOfBirth,
      nationality: profile.nationality,
      idDocumentType: profile.idDocumentType,
      idDocumentNumber: profile.idDocumentNumber,
      phone: profile.phone,
      notificationEmail: profile.notificationEmail,
      addressStreet: profile.addressStreet,
      addressCity: profile.addressCity,
      addressState: profile.addressState,
      addressCountry: profile.addressCountry,
      addressPostalCode: profile.addressPostalCode,
      preferredLanguage: profile.preferredLanguage,
      marketingOptIn: profile.marketingOptIn,
      notificationEmailEnabled: profile.notificationEmailEnabled,
      notificationSmsEnabled: profile.notificationSmsEnabled,
      avatarUrl: profile.avatarUrl,
      socialInstagram: profile.socialInstagram,
      socialFacebook: profile.socialFacebook,
      socialTwitter: profile.socialTwitter,
      socialLinkedin: profile.socialLinkedin,
      travelPurpose: profile.travelPurpose,
      travelBudget: profile.travelBudget,
      travelCompanions: profile.travelCompanions,
      travelAccommodation: profile.travelAccommodation,
      travelDestinationType: profile.travelDestinationType,
      travelInterests: profile.travelInterests,
      travelFrequentFlyer: profile.travelFrequentFlyer,
      travelLoyaltyPrograms: profile.travelLoyaltyPrograms,
      travelNotes: profile.travelNotes,
    });
  }

  /** Wrapper for PpTabBarComponent — casts string to union type */
  handleSetTab(tab: string): void {
    this.activeTab.set(tab as 'personal' | 'contact' | 'preferences' | 'social');
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragOver.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragOver.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragOver.set(false);

    if (this.uploading()) return;

    const file = event.dataTransfer?.files?.[0];
    if (!file) return;

    // Programmatically trigger file selection with this file
    const dt = new DataTransfer();
    dt.items.add(file);
    const input = this.fileInput()?.nativeElement;
    if (input) {
      input.files = dt.files;
      input.dispatchEvent(new Event('change'));
    }
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.saving.set(true);
    this.successMessage.set('');
    this.errorMessage.set('');

    this.profileApi
      .updateProfile(this.form.getRawValue())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (updated: ProfileViewModel) => {
          this.profile.set(updated);
          this.successMessage.set('Perfil actualizado correctamente.');
          this.saving.set(false);
          setTimeout(() => this.successMessage.set(''), 3000);
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible guardar los cambios.');
          this.saving.set(false);
        },
      });
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (!input.files?.length) return;

    const file = input.files[0];

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/avif'];
    if (!allowedTypes.includes(file.type)) {
      this.errorMessage.set('Formato no permitido. Usa JPG, PNG, WebP, GIF o AVIF.');
      input.value = '';
      return;
    }

    // Validate file size (2 MB)
    if (file.size > 2 * 1024 * 1024) {
      this.errorMessage.set('La imagen no puede superar los 2 MB.');
      input.value = '';
      return;
    }

    // Show local preview
    const reader = new FileReader();
    reader.onload = (e) => {
      this.previewUrl.set(e.target?.result as string);
    };
    reader.readAsDataURL(file);

    // Upload to backend
    this.uploading.set(true);
    this.uploadProgress.set(0);
    this.errorMessage.set('');
    this.successMessage.set('');

    this.profileApi
      .uploadAvatar(file)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (event) => {
          if (event.type === HttpEventType.UploadProgress && event.total) {
            this.uploadProgress.set(Math.round((100 * event.loaded) / event.total));
          } else if (event.type === HttpEventType.Response) {
            const body = event.body as AvatarUploadResponse;
            if (body.ok) {
              this.form.patchValue({ avatarUrl: body.avatar_url });
              this.successMessage.set('Foto de perfil actualizada.');
              this.previewUrl.set(null);
            } else {
              this.errorMessage.set(body.message || 'Error al subir la imagen.');
            }
            this.uploading.set(false);
          }
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'Error al subir la imagen.');
          this.uploading.set(false);
          this.previewUrl.set(null);
        },
      });
  }
}
