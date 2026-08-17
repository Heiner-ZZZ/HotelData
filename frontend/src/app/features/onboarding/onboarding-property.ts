import { HttpClient, httpResource } from '@angular/common/http';

import { getErrorMessage } from '../../shared/utils/http-error.util';
import { TermsDialogComponent } from '../../shared/ui/terms-dialog/terms-dialog';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  signal
} from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import {
  FormBuilder,
  FormControl,
  ReactiveFormsModule,
  Validators
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { API_CONFIG } from '../../core/api/api.config';

interface SystemCurrencyDto {
  readonly code: string;
  readonly name: string;
  readonly symbol: string;
  readonly decimals: number;
  readonly active: boolean;
}

interface CountryDto {
  readonly visitor_location_country_id: number;
  readonly country_name: string;
}

interface PropertyTypeOption {
  readonly value: string;
  readonly label: string;
  readonly icon: string;
}

/** E.164 international phone regex (digits 7-15, optional leading +). */
const PHONE_PATTERN = /^\+?[1-9]\d{6,14}$/;

const PROPERTY_TYPES: readonly PropertyTypeOption[] = [
  { value: 'hotel', label: 'Hotel', icon: 'hotel' },
  { value: 'hostal', label: 'Hostal', icon: 'hostel' },
  { value: 'apartamento', label: 'Apartamento', icon: 'apartment' },
  { value: 'bed_breakfast', label: 'Bed & Breakfast', icon: 'breakfast_dining' },
  { value: 'resort', label: 'Resort', icon: 'beach_access' },
  { value: 'cabaña', label: 'Cabaña', icon: 'cabin' },
  { value: 'boutique', label: 'Boutique', icon: 'diamond' }
];

const FALLBACK_CURRENCIES: readonly SystemCurrencyDto[] = [
  { code: 'USD', name: 'Dólar estadounidense', symbol: '$', decimals: 2, active: true },
  { code: 'MXN', name: 'Peso mexicano', symbol: '$', decimals: 2, active: true },
  { code: 'EUR', name: 'Euro', symbol: '€', decimals: 2, active: true },
  { code: 'COP', name: 'Peso colombiano', symbol: '$', decimals: 0, active: true }
];

const FALLBACK_COUNTRIES: readonly CountryDto[] = [
  { visitor_location_country_id: 1, country_name: 'México' },
  { visitor_location_country_id: 2, country_name: 'Colombia' },
  { visitor_location_country_id: 3, country_name: 'Argentina' },
  { visitor_location_country_id: 4, country_name: 'Perú' },
  { visitor_location_country_id: 5, country_name: 'Chile' }
];

type CodeKey = 'digit0' | 'digit1' | 'digit2' | 'digit3' | 'digit4' | 'digit5';

interface SendCodeResponseDto {
  readonly ok: boolean;
  readonly email: string;
  readonly message: string;
}

interface ConfirmCodeResponseDto {
  readonly ok: boolean;
  readonly requires_login: boolean;
  readonly prop_id: number;
  readonly email: string;
  readonly message: string;
}

interface PricingPlanDto {
  readonly band: number;
  readonly label: string;
  readonly min_rooms: number;
  readonly max_rooms: number;
  readonly monthly_usd: number;
  readonly annual_monthly_usd: number;
}

/** Planes visibles del onboarding (3 tarjetas, PLAN §3.2/§14) que agrupan las 6 bandas. */
interface VisiblePlanOption {
  readonly key: 'small' | 'medium' | 'large';
  readonly label: string;
  readonly rangeLabel: string;
  readonly icon: string;
  readonly fromBand: number;
  readonly minRooms: number;
  readonly maxRooms: number;
}

const VISIBLE_PLANS: readonly VisiblePlanOption[] = [
  { key: 'small', label: 'Pequeño', rangeLabel: '1–25', icon: 'bed', fromBand: 1, minRooms: 1, maxRooms: 25 },
  { key: 'medium', label: 'Mediano', rangeLabel: '26–100', icon: 'home_work', fromBand: 3, minRooms: 26, maxRooms: 100 },
  { key: 'large', label: 'Grande', rangeLabel: '101+', icon: 'business', fromBand: 5, minRooms: 101, maxRooms: 10000 },
];

type VisiblePlanKey = 'small' | 'medium' | 'large';

/** Tarjeta visible que corresponde a una cantidad de habitaciones. */
function derivePlanKey(rooms: number): VisiblePlanKey {
  return VISIBLE_PLANS.find((p) => rooms >= p.minRooms && rooms <= p.maxRooms)?.key ?? 'small';
}

interface PaymentMethodOption {
  readonly value: string;
  readonly label: string;
  readonly icon: string;
}

const PAYMENT_METHOD_OPTIONS: readonly PaymentMethodOption[] = [
  { value: 'bank_transfer', label: 'Transferencia', icon: 'account_balance' },
  { value: 'cash_deposit', label: 'Depósito', icon: 'payments' },
  { value: 'manual_online', label: 'Pago en línea', icon: 'currency_exchange' },
];

@Component({
  selector: 'app-onboarding-property',
  imports: [ReactiveFormsModule, RouterLink, TermsDialogComponent],
  templateUrl: './onboarding-property.html',
  styleUrls: [
    '../../../styles/_auth-shell.scss',
    '../../../styles/_form-shell.scss',
    './onboarding-property.scss'
  ],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class OnboardingPropertyComponent {
  private readonly formBuilder = inject(FormBuilder);
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly propertyTypes = PROPERTY_TYPES;
  readonly visiblePlans = VISIBLE_PLANS;
  readonly paymentMethodOptions = PAYMENT_METHOD_OPTIONS;

  // ── Phase state ──
  readonly submitting = signal(false);
  readonly awaitingVerification = signal(false);
  readonly verifyingCode = signal(false);
  readonly sendingCode = signal(false);

  readonly successMessage = signal('');
  readonly errorMessage = signal('');
  readonly passwordVisible = signal(false);

  readonly verificationEmail = signal('');
  readonly codeDigits = signal<string[]>(['', '', '', '', '', '']);

  readonly currentYear = new Date().getFullYear();

  // ── Catalog resources ──
  readonly currenciesResource = httpResource<{
    currencies: SystemCurrencyDto[];
    fallback?: boolean;
  }>(() => `${this.apiConfig.baseUrl}/public/currencies`, {
    parse: (dto) => {
      const raw = (dto as { currencies?: SystemCurrencyDto[] })?.currencies ?? [];
      const cleaned = raw.filter((c) => c?.code && c.active !== false);
      return { currencies: cleaned.length ? cleaned : [...FALLBACK_CURRENCIES] };
    }
  });

  readonly currencies = computed<readonly SystemCurrencyDto[]>(() => {
    const fromApi = this.currenciesResource.value()?.currencies;
    return fromApi && fromApi.length ? fromApi : FALLBACK_CURRENCIES;
  });

  readonly countriesResource = httpResource<{
    countries: CountryDto[];
    fallback?: boolean;
  }>(() => `${this.apiConfig.baseUrl}/public/countries`, {
    parse: (dto) => {
      const raw = (dto as { countries?: CountryDto[] })?.countries ?? [];
      const cleaned = raw.filter(
        (c) => typeof c?.visitor_location_country_id === 'number'
      );
      return { countries: cleaned.length ? cleaned : [...FALLBACK_COUNTRIES] };
    }
  });

  readonly countries = computed<readonly CountryDto[]>(
    () => this.countriesResource.value()?.countries ?? FALLBACK_COUNTRIES
  );

  // ── Pricing plans (catálogo público de bandas) ──────────────────────
  readonly pricingPlansResource = httpResource<{ plans: PricingPlanDto[] }>(
    () => `${this.apiConfig.baseUrl}/public/pricing-plans`,
    {
      parse: (dto) => {
        const raw = (dto as { plans?: PricingPlanDto[] })?.plans ?? [];
        const cleaned = raw.filter(
          (p) =>
            typeof p?.band === 'number' &&
            typeof p?.min_rooms === 'number' &&
            typeof p?.max_rooms === 'number' &&
            typeof p?.monthly_usd === 'number'
        );
        return { plans: cleaned };
      }
    }
  );

  readonly isCatalogsLoading = computed(
    () =>
      this.currenciesResource.isLoading() ||
      this.countriesResource.isLoading() ||
      this.pricingPlansResource.isLoading()
  );

  // ── Combined registration form ──
  readonly onboardingForm = this.formBuilder.nonNullable.group({
    // Account block
    email: ['', [Validators.required, Validators.email]],
    username: ['', [Validators.required, Validators.minLength(3)]],
    user_display_name: [''],
    password: ['', [Validators.required, Validators.minLength(6)]],
    confirm_password: ['', [Validators.required]],

    // Property block
    property_name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(120)]],
    property_type: ['', [Validators.required]],
    contact_phone: ['', [Validators.required, Validators.pattern(PHONE_PATTERN)]],
    country_id: [0, [Validators.required, Validators.min(1)]],
    city: ['', [Validators.required, Validators.minLength(2)]],
    currency: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(3)]],
    total_rooms: [1, [Validators.required, Validators.min(1), Validators.max(10000)]],
    description: ['', [Validators.maxLength(500)]],
    // Ciclo de facturación + método de pago (Fase 6, PLAN §14.1).
    billing_cycle: ['monthly', [Validators.required]],
    payment_method: ['bank_transfer', [Validators.required]],
    // Confirmación explícita del plan derivado (no es de libre elección).
    plan_confirmed: [false, [Validators.requiredTrue]],
    // Aceptación de Términos y Condiciones para Anfitriones (versión vigente).
    terms_accepted: [false, [Validators.requiredTrue]]
  });

  // ── Términos y Condiciones (versión activa desde el backend, nunca hardcodeada) ──
  readonly termsOpen = signal(false);
  readonly termsResource = httpResource<{ version: number } | null>(
    () => `${this.apiConfig.baseUrl}/public/legal?doc_type=terms_hotel_partner`,
    {
      parse: (dto) => {
        const raw = dto as { version?: number } | null;
        if (!raw || typeof raw.version !== 'number') return null;
        return { version: raw.version };
      },
    },
  );
  readonly termsVersion = (): number | null =>
    this.termsResource.value()?.version ?? null;
  readonly termsLoading = (): boolean => this.termsResource.isLoading();
  readonly termsError = (): boolean => !!this.termsResource.error();

  openTerms(event?: Event): void {
    // El botón vive dentro del <label> del checkbox: no debe alternarlo.
    event?.preventDefault();
    event?.stopPropagation();
    this.termsOpen.set(true);
  }

  closeTerms(): void {
    this.termsOpen.set(false);
  }

  // ── Plan derivado de total_rooms (banda + precio en vivo) ──────────
  readonly totalRooms = toSignal(
    this.onboardingForm.controls.total_rooms.valueChanges,
    { initialValue: this.onboardingForm.controls.total_rooms.value }
  );

  readonly derivedPlan = computed<PricingPlanDto | null>(() => {
    const rooms = this.totalRooms() ?? 0;
    const plans = this.pricingPlansResource.value()?.plans ?? [];
    return plans.find((p) => rooms >= p.min_rooms && rooms <= p.max_rooms) ?? null;
  });

  /** USD ahorrados al año pagando el plan por adelantado: (mensual − anual) × 12. */
  readonly planAnnualSavings = computed<number>(() => {
    const plan = this.derivedPlan();
    if (!plan) return 0;
    return Math.max(0, Math.round((plan.monthly_usd - plan.annual_monthly_usd) * 12));
  });

  /** % de descuento del plan anual (~22–27%) — solo para el badge. */
  readonly planAnnualDiscountPct = computed<number>(() => {
    const plan = this.derivedPlan();
    if (!plan || plan.monthly_usd <= 0) return 0;
    return Math.round((1 - plan.annual_monthly_usd / plan.monthly_usd) * 100);
  });

  /** Ciclo elegido (mensual/anual) como signal reactivo. */
  readonly billingCycle = toSignal(
    this.onboardingForm.controls.billing_cycle.valueChanges,
    { initialValue: this.onboardingForm.controls.billing_cycle.value }
  );

  /** Tarjeta derivada de las habitaciones (la que corresponde a total_rooms). */
  readonly derivedPlanKey = computed<VisiblePlanKey | null>(() => {
    const rooms = this.totalRooms() ?? 0;
    return (
      VISIBLE_PLANS.find((p) => rooms >= p.minRooms && rooms <= p.maxRooms)?.key ?? null
    );
  });

  /** Tarjeta elegida por el dueño (radio). Se ancla a la derivada si cambian las habitaciones. */
  readonly selectedPlanKey = signal<VisiblePlanKey>(
    derivePlanKey(this.onboardingForm.controls.total_rooms.value)
  );

  /** True si el dueño marcó una tarjeta que no corresponde a sus habitaciones. */
  readonly planMismatch = computed<boolean>(() => {
    const derived = this.derivedPlanKey();
    return derived !== null && this.selectedPlanKey() !== derived;
  });

  /** Plan visible correspondiente a las habitaciones (para labels y mensajes). */
  readonly derivedVisiblePlan = computed<VisiblePlanOption | null>(() => {
    const key = this.derivedPlanKey();
    return key ? (VISIBLE_PLANS.find((p) => p.key === key) ?? null) : null;
  });

  // Si cambian las habitaciones, la tarjeta elegida vuelve a la derivada.
  private readonly syncPlanSelection = effect(() => {
    const derived = this.derivedPlanKey();
    if (derived) this.selectedPlanKey.set(derived);
  });

  /** Selección manual de tarjeta (radio). Si no coincide con la derivación, desmarca la confirmación. */
  selectPlan(key: VisiblePlanKey): void {
    this.selectedPlanKey.set(key);
    if (key !== this.derivedPlanKey()) {
      this.onboardingForm.controls.plan_confirmed.setValue(false);
    }
  }

  /** Precio "desde" de cada tarjeta (mínimo mensual de su grupo de bandas). */
  readonly visiblePlanPrices = computed<Record<string, number>>(() => {
    const plans = this.pricingPlansResource.value()?.plans ?? [];
    const result: Record<string, number> = {};
    for (const p of VISIBLE_PLANS) {
      result[p.key] = plans.find((b) => b.band === p.fromBand)?.monthly_usd ?? 0;
    }
    return result;
  });

  /** Precio del plan derivado según el ciclo elegido (mensual vs anual). */
  readonly currentPlanPrice = computed<number>(() => {
    const plan = this.derivedPlan();
    if (!plan) return 0;
    return this.billingCycle() === 'annual'
      ? plan.annual_monthly_usd
      : plan.monthly_usd;
  });

  // Si cambia la banda derivada, la confirmación anterior deja de ser válida
  // (el dueño debe re-confirmar su nuevo plan antes de enviar).
  private lastConfirmedBand: number | null = null;
  private readonly resetPlanConfirmation = effect(() => {
    const band = this.derivedPlan()?.band ?? null;
    if (band !== this.lastConfirmedBand) {
      this.lastConfirmedBand = band;
      this.onboardingForm.controls.plan_confirmed.setValue(false);
    }
  });

  // ── Six-digit verification form (mirrors register-page pattern) ──
  readonly codeForm = this.formBuilder.nonNullable.group({
    digit0: ['', [Validators.required, Validators.maxLength(1), Validators.pattern('[0-9]')]],
    digit1: ['', [Validators.required, Validators.maxLength(1), Validators.pattern('[0-9]')]],
    digit2: ['', [Validators.required, Validators.maxLength(1), Validators.pattern('[0-9]')]],
    digit3: ['', [Validators.required, Validators.maxLength(1), Validators.pattern('[0-9]')]],
    digit4: ['', [Validators.required, Validators.maxLength(1), Validators.pattern('[0-9]')]],
    digit5: ['', [Validators.required, Validators.maxLength(1), Validators.pattern('[0-9]')]]
  });

  private readonly codeControlMap: Record<CodeKey, FormControl<string>> = {
    digit0: this.codeForm.controls.digit0,
    digit1: this.codeForm.controls.digit1,
    digit2: this.codeForm.controls.digit2,
    digit3: this.codeForm.controls.digit3,
    digit4: this.codeForm.controls.digit4,
    digit5: this.codeForm.controls.digit5
  };

  readonly codeControls: readonly FormControl<string>[] = [
    this.codeControlMap.digit0,
    this.codeControlMap.digit1,
    this.codeControlMap.digit2,
    this.codeControlMap.digit3,
    this.codeControlMap.digit4,
    this.codeControlMap.digit5
  ];

  // ── Password toggle ──
  togglePasswordVisibility() {
    this.passwordVisible.update((v) => !v);
  }

  // ── Code digit handlers ──
  // `index` is `number` because @for's `$index` is widened to number in the
  // template; we guard with `CodeKey`-safe casts and `index < 5` below.
  onDigitInput(index: number, event: Event): void {
    if (index < 0 || index > 5) return;
    const input = event.target as HTMLInputElement;
    const digit = input.value.replace(/\D/g, '').slice(0, 1);
    const newDigits = [...this.codeDigits()];
    newDigits[index] = digit;
    this.codeDigits.set(newDigits);
    this.codeControlMap[`digit${index}` as CodeKey].setValue(digit);
    if (digit && index < 5) {
      document
        .querySelector<HTMLInputElement>(`#onboarding-code-digit-${index + 1}`)
        ?.focus();
    }
  }

  onDigitKeydown(index: number, event: KeyboardEvent): void {
    if (index < 0 || index > 5) return;
    if (event.key === 'Backspace' && !this.codeDigits()[index] && index > 0) {
      document
        .querySelector<HTMLInputElement>(`#onboarding-code-digit-${index - 1}`)
        ?.focus();
    } else if (event.key === 'Enter') {
      this.confirmCode();
    }
  }

  onDigitPaste(event: ClipboardEvent): void {
    event.preventDefault();
    const text = event.clipboardData?.getData('text') ?? '';
    const digits = text.replace(/\D/g, '').slice(0, 6).split('');
    const newDigits: string[] = ['', '', '', '', '', ''];
    digits.forEach((d, i) => { newDigits[i] = d; });
    this.codeDigits.set(newDigits);
    for (let i = 0; i < 6; i++) {
      this.codeControlMap[`digit${i}` as CodeKey].setValue(newDigits[i]);
    }
    const nextEmpty = newDigits.findIndex((d) => !d);
    const focusIndex = nextEmpty >= 0 ? nextEmpty : 5;
    document
      .querySelector<HTMLInputElement>(`#onboarding-code-digit-${focusIndex}`)
      ?.focus();
  }

  // ── Phase 1: submit → send verification code ──
  submit(): void {
    if (this.planMismatch()) {
      this.onboardingForm.markAllAsTouched();
      this.errorMessage.set(
        `Tu plan por ${this.totalRooms() ?? 0} habitaciones es ${this.derivedVisiblePlan()?.label ?? 'el sugerido'}. Selecciona la tarjeta sugerida para continuar.`
      );
      return;
    }

    if (this.onboardingForm.invalid || this.submitting()) {
      this.onboardingForm.markAllAsTouched();
      return;
    }

    if (!this.onboardingForm.controls.terms_accepted.value) {
      this.onboardingForm.controls.terms_accepted.markAsTouched();
      this.errorMessage.set(
        'Debes aceptar los Términos y Condiciones para anfitriones para continuar.'
      );
      return;
    }

    const raw = this.onboardingForm.getRawValue();
    if (raw.password !== raw.confirm_password) {
      this.errorMessage.set('Las contraseñas no coinciden.');
      return;
    }

    this.sendingCode.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    this.http
      .post<SendCodeResponseDto>(
        `${this.apiConfig.baseUrl}/auth/register-property/send-code`,
        {
          email: raw.email,
          username: raw.username,
          user_display_name: raw.user_display_name || undefined,
          password: raw.password,
          property_name: raw.property_name,
          property_type: raw.property_type,
          contact_phone: raw.contact_phone,
          country_id: raw.country_id,
          city: raw.city,
          currency: raw.currency,
          total_rooms: raw.total_rooms,
          plan_band: this.derivedPlan()?.band,
          billing_cycle: raw.billing_cycle,
          payment_method: raw.payment_method,
          description: raw.description || undefined,
          accepted_terms_version: this.termsVersion() ?? undefined
        },
        { withCredentials: true }
      )
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.sendingCode.set(false);
          this.verificationEmail.set(response.email);
          this.successMessage.set(response.message);
          this.resetCodeDigits();
          this.awaitingVerification.set(true);
          setTimeout(() => {
            document
              .querySelector<HTMLInputElement>('#onboarding-code-digit-0')
              ?.focus();
          }, 100);
        },
        error: (error: unknown) => {
          this.sendingCode.set(false);
          this.errorMessage.set(
            getErrorMessage(error) || 'Error al procesar tu registro. Intenta nuevamente.'
          );
        }
      });
  }

  // ── Phase 2: verify code → create user + property ──
  confirmCode(): void {
    const code = this.codeDigits().join('');
    if (code.length !== 6) {
      this.errorMessage.set('Ingresa el código completo de 6 dígitos.');
      return;
    }

    this.verifyingCode.set(true);
    this.errorMessage.set('');
    this.successMessage.set('');

    this.http
      .post<ConfirmCodeResponseDto>(
        `${this.apiConfig.baseUrl}/auth/register-property/confirm-code`,
        {
          email: this.verificationEmail(),
          code
        },
        { withCredentials: true }
      )
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          this.verifyingCode.set(false);
          this.successMessage.set(
            response.message ||
              'Tu alojamiento fue registrado. Inicia sesión para acceder a tu panel.'
          );
          setTimeout(() => {
            void this.router.navigate(['/login'], {
              queryParams: { welcome: 'partner' }
            });
          }, 1800);
        },
        error: (error: unknown) => {
          this.verifyingCode.set(false);
          this.resetCodeDigits();
          document
            .querySelector<HTMLInputElement>('#onboarding-code-digit-0')
            ?.focus();
          this.errorMessage.set(
            getErrorMessage(error) || 'Error al verificar el código. Solicita uno nuevo.'
          );
        }
      });
  }

  resendCode(): void {
    // Phase 1 data is already submitted; trigger the same endpoint again.
    this.submit();
  }

  cancelVerification(): void {
    this.awaitingVerification.set(false);
    this.resetCodeDigits();
    this.errorMessage.set('');
    this.successMessage.set('');
  }

  /** Reset verification state so the user can re-discover the focus target. */
  private resetCodeDigits(): void {
    this.codeDigits.set(['', '', '', '', '', '']);
    for (const key of ['digit0', 'digit1', 'digit2', 'digit3', 'digit4', 'digit5'] as CodeKey[]) {
      this.codeControlMap[key].setValue('');
    }
  }
}
