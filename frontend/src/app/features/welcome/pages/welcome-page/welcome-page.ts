import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  signal,
} from '@angular/core';
import { httpResource } from '@angular/common/http';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../../core/auth/auth.service';
import { ThemeService } from '../../../../core/theme/theme.service';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { BookingSearchBarComponent, type BookingSearchValues } from '../../../../shared/ui/booking-search-bar/booking-search-bar';
import { CarouselControlsComponent } from '../../../../shared/ui/carousel-controls/carousel-controls';
import { TermsDialogComponent } from '../../../../shared/ui/terms-dialog/terms-dialog';
import { API_CONFIG } from '../../../../core/api/api.config';

import {
  CURRENCY_STORAGE_KEY,
  FALLBACK_CURRENCIES,
  type FeaturedHotel,
  type SystemCurrencyDto,
} from '../../models/welcome.models';
import { currencyFlag, mapFeaturedHotels } from '../../mappers/welcome.mapper';
import {
  loadWelcomeSearchState,
  saveWelcomeSearchState,
} from '../../services/welcome-search-state';

@Component({
  selector: 'app-welcome-page',
  imports: [RouterLink, BookingSearchBarComponent, CarouselControlsComponent, TermsDialogComponent],
  templateUrl: './welcome-page.html',
  styleUrls: [
    '../../../../../styles/_auth-shell.scss',
    './welcome-page.scss',
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WelcomePageComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly propertyCtx = inject(PropertyContextService);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly theme = inject(ThemeService);
  private readonly destroyRef = inject(DestroyRef);

  readonly year = new Date().getFullYear();

  // ── Documentos legales (footer) — cargados del backend por el TermsDialog ──
  readonly legalOpen = signal<string | null>(null);

  openLegal(docType: string): void {
    this.legalOpen.set(docType);
  }

  closeLegal(): void {
    this.legalOpen.set(null);
  }

  // ── Search form ─────────────────────────────────────────────────────────

  /** Hoy en fecha LOCAL (YYYY-MM-DD) — no UTC: en husos negativos,
   *  toISOString() devolvería mañana y rompería minDate + el saneo de
   *  fechas pasadas del estado guardado. Reactivo: refresca a medianoche
   *  y al volver a la pestaña (mismo ritual que hotel-search-page). */
  readonly today = signal(this.localToday());
  private midnightTimer: ReturnType<typeof setTimeout> | null = null;

  /** Estado inicial del booking-bar compartido: lo que el usuario dejó
   *  guardado la última vez (o defaults si no hay nada persistido).
   *  Computed para que al cruzar medianoche las fechas pasadas se saneen
   *  solas (loadWelcomeSearchState descarta checkIn < today). */
  readonly initialSearch = computed<BookingSearchValues>(
    () => loadWelcomeSearchState(this.today()) ?? { destination: '', checkIn: '', checkOut: '', adults: 2, children: 0, rooms: 1 },
  );

  /** Último valor del booking-bar (para persistencia en vivo debounced). */
  private readonly latestValues = signal<BookingSearchValues>(this.initialSearch());

  /** Persistencia en vivo: cada cambio del booking-bar se guarda (debounced)
   *  para que al volver al welcome el estado no se pierda. */
  onValueChange(values: BookingSearchValues): void {
    this.latestValues.set(values);
  }

  /** Buscar: persiste y navega a /search con los query params canónicos
   *  (omite los valores por defecto para mantener la URL limpia). */
  onSearch(values: BookingSearchValues): void {
    this.persistSearchState(values);

    const params: Record<string, string> = {};
    if (values.destination.trim()) params['destination'] = values.destination.trim();
    if (values.checkIn) params['check_in'] = values.checkIn;
    if (values.checkOut) params['check_out'] = values.checkOut;
    if (values.adults !== 2) params['adults'] = String(values.adults);
    if (values.children !== 0) params['children'] = String(values.children);
    if (values.rooms !== 1) params['rooms'] = String(values.rooms);

    const qs = new URLSearchParams(params).toString();
    void this.router.navigateByUrl(qs ? `/search?${qs}` : '/search');
  }

  /** Persiste el estado del booking bar a localStorage (tolerante a fallos). */
  private persistSearchState(values: BookingSearchValues): void {
    saveWelcomeSearchState(values);
  }

  // ── Featured hotels ─────────────────────────────────────────────────────

  readonly featuredHotelsResource = httpResource<{ items: FeaturedHotel[] }>(
    () => `${this.apiConfig.baseUrl}/hotels/availability?sort_by=rating&page_size=3&content_only=true`,
    {
      parse: (dto) => ({ items: mapFeaturedHotels(dto as { items?: {
        prop_id: number; display_name: string; prop_starrating: number | null;
        prop_review_score: number | null; image_url: string | null;
        destination_labels: string[]; min_nightly_rate_label: string | null;
      }[] }) }),
    },
  );

  readonly featuredHotels = computed(() => this.featuredHotelsResource.value()?.items ?? []);

  hotelDetailHref(propId: number): string {
    return `/hotels/${propId}`;
  }

  // ── Mini-carrusel de las cards destacadas (puntitos tipo comparador) ──

  /** Slide activo por hotel (keyed por prop_id). */
  readonly welcomeSlides = signal<Record<number, number>>({});

  /** Índice activo de la galería del hotel (0 si nunca se tocó). */
  welcomeSlide(propId: number): number {
    return this.welcomeSlides()[propId] ?? 0;
  }

  /** Offset translateX del track de la galería. */
  welcomeOffset(propId: number, slide: number): string {
    return `translateX(-${slide * 100}%)`;
  }

  /**
   * Cambia el slide sin disparar la navegación del <a> contenedor.
   * `total` permite wrap-around (flechas prev/next), igual que el comparador:
   * `((idx % total) + total) % total` — índices válidos pasan sin cambio.
   */
  goToSlide(propId: number, idx: number, total: number, event?: Event): void {
    event?.preventDefault();
    event?.stopPropagation();
    const clamped = total > 0 ? ((idx % total) + total) % total : 0;
    this.welcomeSlides.update((m) => ({ ...m, [propId]: clamped }));
  }

  // ── Auto-rotación al pasar el mouse (patrón hotel-card de búsqueda) ──

  /** Intervalos de rotación por hotel (keyed por prop_id). */
  private readonly rotationTimers = new Map<number, ReturnType<typeof setInterval>>();

  /** Transición desactivada por hotel: el wrap de la rotación no debe
   *  animar el scroll-back visible hacia la primera foto. */
  readonly welcomeTransitions = signal<Record<number, boolean>>({});

  welcomeNoTransition(propId: number): boolean {
    return this.welcomeTransitions()[propId] ?? false;
  }

  private hotelImagesCount(propId: number): number {
    return this.featuredHotels().find((h) => h.id === propId)?.images.length ?? 0;
  }

  /** Respecta WCAG 2.3.3: con prefers-reduced-motion la galería no rota sola. */
  private prefersReducedMotion(): boolean {
    return typeof window.matchMedia === 'function'
      && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  /** Inicia la auto-rotación de la card mientras el mouse está encima. */
  startRotation(propId: number): void {
    const total = this.hotelImagesCount(propId);
    if (total <= 1 || this.prefersReducedMotion()) return;
    const existing = this.rotationTimers.get(propId);
    if (existing) clearInterval(existing);
    const timer = setInterval(() => {
      const current = this.welcomeSlide(propId);
      const next = (current + 1) % total;
      if (next === 0) {
        // Wrap: sin transición para no animar el salto hacia atrás.
        this.welcomeTransitions.update((m) => ({ ...m, [propId]: true }));
        this.welcomeSlides.update((m) => ({ ...m, [propId]: 0 }));
        setTimeout(() => this.welcomeTransitions.update((m) => ({ ...m, [propId]: false })), 50);
      } else {
        this.welcomeSlides.update((m) => ({ ...m, [propId]: next }));
      }
    }, 3500);
    this.rotationTimers.set(propId, timer);
  }

  /** Detiene la rotación y vuelve a la primera foto (como el hotel-card). */
  stopRotation(propId: number): void {
    const timer = this.rotationTimers.get(propId);
    if (timer) {
      clearInterval(timer);
      this.rotationTimers.delete(propId);
    }
    this.welcomeSlides.update((m) => ({ ...m, [propId]: 0 }));
    this.welcomeTransitions.update((m) => ({ ...m, [propId]: false }));
  }

  /** Flechas prev/next: navegan con wrap y reinician la rotación solo si ya
   *  estaba corriendo (igual que nextImage/prevImage del hotel-card).
   *  El evento ya lo corta el componente compartido (preventDefault +
   *  stopPropagation), por eso es opcional. */
  stepSlide(propId: number, dir: 1 | -1, event?: Event): void {
    const total = this.hotelImagesCount(propId);
    this.goToSlide(propId, this.welcomeSlide(propId) + dir, total, event);
    if (this.rotationTimers.has(propId)) {
      this.startRotation(propId);
    }
  }

  // ── Hover de la card: revela las flechas del carrusel compartido ──

  /** Hoteles con el mouse encima: el componente compartido muestra sus
   *  flechas (modo reveal) solo mientras la card está hovereada. */
  readonly hoveredHotels = signal<Set<number>>(new Set());

  onCardEnter(propId: number): void {
    this.hoveredHotels.update((s) => new Set(s).add(propId));
    this.startRotation(propId);
  }

  onCardLeave(propId: number): void {
    this.hoveredHotels.update((s) => {
      const next = new Set(s);
      next.delete(propId);
      return next;
    });
    this.stopRotation(propId);
  }

  readonly STAR_5 = [0, 1, 2, 3, 4];

  // ── Auth toast ──────────────────────────────────────────────────────────

  readonly showAuthToast = signal(false);

  /**
   * El toast se mantiene hasta que el usuario lo cierre o use una de sus
   * acciones: el auto-dismiss a 8s hacía desaparecer una oferta con botones
   * mientras se leía (WCAG 2.2.1 Timing Adjustable — la información no debe
   * caducar sin control).
   */
  handleHotelClick(hotelId: number, event: Event): void {
    event.preventDefault();
    if (this.authService.isAuthenticated()) {
      void this.router.navigateByUrl(`/hotels/${hotelId}`);
      return;
    }
    this.showAuthToast.set(true);
  }

  dismissAuthToast(): void {
    this.showAuthToast.set(false);
  }

  readonly hasSession = computed(
    () => this.authService.isAuthenticated() && this.authService.sessionLoaded(),
  );

  // ── Currency chip ───────────────────────────────────────────────────────

  readonly currenciesResource = httpResource<{ currencies: SystemCurrencyDto[] }>(
    () => `${this.apiConfig.baseUrl}/public/currencies`,
    {
      parse: (dto) => {
        const raw = (dto as { currencies?: SystemCurrencyDto[] })?.currencies ?? [];
        const cleaned = raw.filter((c) => c?.code && c.active !== false);
        return { currencies: cleaned.length ? cleaned : [...FALLBACK_CURRENCIES] };
      },
    },
  );

  readonly currencies = computed<readonly SystemCurrencyDto[]>(() => {
    const fromApi = this.currenciesResource.value()?.currencies;
    return fromApi && fromApi.length ? fromApi : FALLBACK_CURRENCIES;
  });

  readonly selectedCurrency = signal<string>(this.readStoredCurrency());

  constructor() {
    // Calendario dinámico: hoy reactivo y refresco a medianoche / foco.
    this.scheduleMidnightRefresh();
    document.addEventListener('visibilitychange', this.onVisibilityChange);
    window.addEventListener('focus', this.onFocus);
    this.destroyRef.onDestroy(() => {
      if (this.midnightTimer !== null) clearTimeout(this.midnightTimer);
      document.removeEventListener('visibilitychange', this.onVisibilityChange);
      window.removeEventListener('focus', this.onFocus);
    });

    // El landing público /welcome SIEMPRE se ve en modo claro, sin importar
    // la preferencia del usuario (la que manda en el resto de la app). Se
    // libera al salir de la ruta para que el resto respete su preferencia.
    this.theme.forceLight(true);
    this.destroyRef.onDestroy(() => this.theme.forceLight(false));
    this.destroyRef.onDestroy(() => {
      for (const timer of this.rotationTimers.values()) clearInterval(timer);
      this.rotationTimers.clear();
    });

    effect(() => {
      if (this.hasSession()) {
        const homeHref = this.authService.authState().homeHref;
        void this.router.navigateByUrl(this.authService.resolveDefaultDestination(homeHref));
      }
    });

    effect(() => {
      const code = this.selectedCurrency();
      if (!code) return;
      this.propertyCtx.setCurrency(code, [code]);
    });

    // Persistencia en vivo (debounced): si el usuario edita el booking bar
    // pero navega a otra parte sin pulsar Buscar, el estado no se pierde.
    // El destination-autocomplete emite por carácter, así que el debounce
    // evita escribir localStorage en cada tecla. onCleanup cancela el timer
    // si el componente se destruye antes de los 600ms.
    effect((onCleanup) => {
      const values = this.latestValues();
      const timer = setTimeout(() => {
        saveWelcomeSearchState(values);
      }, 600);
      onCleanup(() => clearTimeout(timer));
    });
  }

  onCurrencyChange(code: string): void {
    if (!code || code === this.selectedCurrency()) return;
    this.selectedCurrency.set(code);
    this.writeStoredCurrency(code);
  }

  /** Delegates to the mapper for the flag emoji. */
  currencyFlag(code: string): string {
    return currencyFlag(code);
  }

  // ── Calendario dinámico (hoy reactivo) ────────────────────────────────
  private localToday(): string {
    return new Date().toLocaleDateString('sv-SE');
  }

  private refreshToday(): void {
    this.today.set(this.localToday());
  }

  private scheduleMidnightRefresh(): void {
    // Tests (Jest/jsdom) no deben bloquear `whenStable()` con un timer de ~9h.
    const g = globalThis as unknown as { jest?: unknown; vi?: unknown };
    const isJsdom = typeof navigator !== 'undefined' && /jsdom/i.test(navigator.userAgent);
    if (g.jest || g.vi || isJsdom) return;
    const now = new Date();
    const nextMidnight = new Date(now);
    nextMidnight.setHours(24, 0, 0, 0);
    this.midnightTimer = setTimeout(() => {
      this.refreshToday();
      this.scheduleMidnightRefresh();
    }, nextMidnight.getTime() - now.getTime());
  }

  private readonly onVisibilityChange = (): void => {
    if (!document.hidden) this.refreshToday();
  };

  private readonly onFocus = (): void => this.refreshToday();

  // ── LocalStorage helpers ────────────────────────────────────────────────

  private readStoredCurrency(): string {
    const v = localStorage.getItem(CURRENCY_STORAGE_KEY);
    if (v && v.trim().length === 3) return v.trim().toUpperCase();
    // First-time visitor: fall back to the property context's default
    // currency (also 'USD' on a fresh install, but this codepath keeps the
    // single source of truth in PropertyContextService instead of leaking
    // a literal that drifts over time).
    return this.propertyCtx.currentCurrency();
  }

  private writeStoredCurrency(code: string): void {
    localStorage.setItem(CURRENCY_STORAGE_KEY, code.toUpperCase());
  }
}
