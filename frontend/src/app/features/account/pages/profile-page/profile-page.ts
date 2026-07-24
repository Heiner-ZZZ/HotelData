import { HttpEventType } from '@angular/common/http';
import { httpResource } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  ElementRef,
  HostListener,
  inject,
  signal,
  viewChild,
  ViewEncapsulation,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { AuthService } from '../../../../core/auth/auth.service';
import { ToastService } from '../../../../shared/services/toast.service';
import type { ApiError } from '../../../../core/api/api-error.model';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PpHeroComponent } from './partials/pp-hero';
import { PpTabBarComponent } from './partials/pp-tab-bar';
import { PpPersonalFormComponent } from './partials/pp-personal-form';
import { PpContactFormComponent } from './partials/pp-contact-form';
import { PpPreferencesFormComponent } from './partials/pp-preferences-form';
import { PpAvatarSectionComponent } from './partials/pp-avatar-section';
import { PpTravelSectionComponent } from './partials/pp-travel-section';
import { ImageLightboxComponent } from '../../../../shared/ui/image-lightbox/image-lightbox';
import type { ProfileViewModel } from '../../models/profile.model';
import type { SelectOption } from '../../models/profile.model';
import {
  DOCUMENT_TYPES,
  TRAVEL_ACCOMMODATION_OPTIONS,
  TRAVEL_BUDGET_OPTIONS,
  TRAVEL_COMPANIONS_OPTIONS,
  TRAVEL_DESTINATION_OPTIONS,
  TRAVEL_PURPOSE_OPTIONS,
} from '../../models/profile.model';
import type { AvatarUploadResponse } from '../../services/profile-api.service';
import { ProfileApiService } from '../../services/profile-api.service';

import type { ProfileDto } from '../../models/profile.dto';
import { mapProfileDtoToViewModel } from '../../mappers/profile.mapper';

/** CamelCase form keys → snake_case API keys. */
const FORM_TO_PAYLOAD: Record<string, string> = {
  displayName: 'display_name',
  dateOfBirth: 'date_of_birth',
  nationality: 'nationality',
  idDocumentType: 'id_document_type',
  idDocumentNumber: 'id_document_number',
  phone: 'phone',
  notificationEmail: 'notification_email',
  addressStreet: 'address_street',
  addressCity: 'address_city',
  addressState: 'address_state',
  addressCountry: 'address_country',
  addressPostalCode: 'address_postal_code',
  preferredLanguage: 'preferred_language',
  marketingOptIn: 'marketing_opt_in',
  notificationEmailEnabled: 'notification_email_enabled',
  notificationSmsEnabled: 'notification_sms_enabled',
  avatarUrl: 'avatar_url',
  socialInstagram: 'social_instagram',
  socialFacebook: 'social_facebook',
  socialTwitter: 'social_twitter',
  socialLinkedin: 'social_linkedin',
  travelPurpose: 'travel_purpose',
  travelBudget: 'travel_budget',
  travelCompanions: 'travel_companions',
  travelAccommodation: 'travel_accommodation',
  travelDestinationType: 'travel_destination_type',
  travelInterests: 'travel_interests',
  travelFrequentFlyer: 'travel_frequent_flyer',
  travelLoyaltyPrograms: 'travel_loyalty_programs',
  travelNotes: 'travel_notes',
};

function formToPayload(formValue: Record<string, unknown>): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  for (const [camel, snake] of Object.entries(FORM_TO_PAYLOAD)) {
    if (camel in formValue) {
      payload[snake] = formValue[camel];
    }
  }
  return payload;
}

@Component({
  selector: 'app-profile-page',
  imports: [ErrorStateComponent, LoadingStateComponent, ReactiveFormsModule,
    PpHeroComponent, PpTabBarComponent, PpPersonalFormComponent, PpContactFormComponent,
    PpPreferencesFormComponent, PpAvatarSectionComponent, ImageLightboxComponent, PpTravelSectionComponent],
  templateUrl: './profile-page.html',
  styleUrl: './profile-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
})
export class ProfilePageComponent {
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);
  private readonly profileApi = inject(ProfileApiService);
  private readonly authService = inject(AuthService);
  private readonly toast = inject(ToastService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly Math = Math;

  readonly fileInput = viewChild<ElementRef<HTMLInputElement>>('fileInput');

  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly uploading = signal(false);
  readonly uploadProgress = signal(0);
  readonly errorMessage = signal<string>('');
  readonly profile = signal<ProfileViewModel | null>(null);
  readonly previewUrl = signal<string | null>(null);
  readonly dragOver = signal(false);
  readonly activeTab = signal<'personal' | 'contact' | 'preferences' | 'social'>('personal');
  readonly lightboxOpen = signal(false);
  readonly lightboxImageUrl = signal<string>('');

  // ═══ Data loading — httpResource (replaces manual GET + subscribe) ═══
  readonly profileResource = httpResource<ProfileViewModel>(() => '/account/profile', {
    parse: (dto) => mapProfileDtoToViewModel(dto as ProfileDto),
  });

  readonly tabs = computed(() => {
    const allTabs = [
      { key: 'personal' as const, label: 'Personal', icon: 'badge' },
      { key: 'contact' as const, label: 'Contacto', icon: 'contact_mail' },
      { key: 'social' as const, label: 'Redes y viajes', icon: 'travel_explore' },
      { key: 'preferences' as const, label: 'Preferencias', icon: 'settings' },
    ];
    // Only guests see Redes y viajes; admin/staff tabs are Personal, Contacto, Preferencias
    const role = this.profile()?.primaryRole;
    if (role && role !== 'cliente') {
      return allTabs.filter(t => t.key !== 'social');
    }
    return allTabs;
  });

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
    // React when profile data arrives from httpResource
    effect(() => {
      const p = this.profileResource.value();
      if (p) {
        this.profile.set(p);
        this.patchForm(p);
      }
    });

    effect(() => {
      this.loading.set(this.profileResource.isLoading());
    });

    effect(() => {
      const err = this.profileResource.error();
      if (err) {
        const message = err.message || 'No fue posible cargar tu perfil.';
        this.errorMessage.set(message);
        this.toast.error(message);
      }
    });

    // ── Tab → URL sync (reads query param on load, writes on change) ──
    const tabParam = this.route.snapshot.queryParamMap.get('tab');
    if (tabParam === 'contact' || tabParam === 'preferences' || tabParam === 'social') {
      this.activeTab.set(tabParam);
    }

    effect(() => {
      const tab = this.activeTab();
      const current = this.route.snapshot.queryParamMap.get('tab');
      if (tab !== 'personal' && tab !== current) {
        void this.router.navigate([], { queryParams: { tab }, queryParamsHandling: 'merge', replaceUrl: true });
      } else if (tab === 'personal' && current) {
        void this.router.navigate([], { queryParams: { tab: null }, queryParamsHandling: 'merge', replaceUrl: true });
      }
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

  openAvatarLightbox(): void {
    const current = this.profile();
    const preview = this.previewUrl();
    if (preview) {
      this.lightboxImageUrl.set(preview);
    } else if (current?.avatarUrl) {
      this.lightboxImageUrl.set(current.avatarUrl);
    } else {
      return;
    }
    this.lightboxOpen.set(true);
  }

  closeAvatarLightbox(): void {
    this.lightboxOpen.set(false);
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

    const rawForm = this.form.getRawValue();
    const payload = formToPayload(rawForm);

    this.profileApi
      .updateProfile(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (updated: ProfileViewModel) => {
          this.profile.set(updated);
          this.patchForm(updated);
          // Sync avatar to auth service so top-nav refreshes
          this.authService.updateAvatar(updated.avatarUrl);
          this.toast.success('Perfil actualizado correctamente.');
          this.saving.set(false);
        },
        error: (error: ApiError) => {
          this.toast.error(error.message || 'No fue posible guardar los cambios.');
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
      this.toast.error('Formato no permitido. Usa JPG, PNG, WebP, GIF o AVIF.');
      input.value = '';
      return;
    }

    // Validate file size (2 MB)
    if (file.size > 2 * 1024 * 1024) {
      this.toast.error('La imagen no puede superar los 2 MB.');
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
              // Immediately update the profile signal so the hero avatar refreshes
              const current = this.profile();
              if (current) {
                this.profile.set({ ...current, avatarUrl: body.avatar_url });
              }
              // Also sync to auth service so the top-nav avatar refreshes
              this.authService.updateAvatar(body.avatar_url);
              this.toast.success('Foto de perfil actualizada.');
              this.previewUrl.set(null);
            } else {
              this.toast.error(body.message || 'Error al subir la imagen.');
            }
            this.uploading.set(false);
          }
        },
        error: (error: ApiError) => {
          this.toast.error(error.message || 'Error al subir la imagen.');
          this.uploading.set(false);
          this.previewUrl.set(null);
        },
      });
  }
}
