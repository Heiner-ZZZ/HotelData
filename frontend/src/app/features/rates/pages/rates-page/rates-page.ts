import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal, computed } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { distinctUntilChanged, forkJoin, map, of, switchMap } from 'rxjs';

import type { ApiError } from '../../../../core/api/api-error.model';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { RatePlanOption, RatesViewModel } from '../../models/rates.model';
import { RatesApiService } from '../../services/rates-api.service';
import { RatePlanTableComponent } from '../../components/rate-plan-table/rate-plan-table';
import { RateCalendarTableComponent } from '../../components/rate-calendar-table/rate-calendar-table';
import { AiSuggestDirective } from '../../../../core/directives/ai-suggest.directive';

@Component({
  selector: 'app-rates-page',
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    PageHeaderComponent,
    PropertySelectorComponent,
    ReactiveFormsModule,
    RatePlanTableComponent,
    RateCalendarTableComponent,
    AiSuggestDirective
  ],
  templateUrl: './rates-page.html',
  styleUrl: './rates-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class RatesPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly api = inject(RatesApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly formBuilder = inject(FormBuilder);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<RatesViewModel | null>(null);
  readonly ratePlanOptions = signal<RatePlanOption[]>([]);
  readonly message = signal('');
  readonly errorMessage = signal('');

  readonly selectedPropId = signal(0);
  readonly selectedLabel = signal('');

  /* ── Forms ── */
  readonly planForm = this.formBuilder.nonNullable.group({
    name: ['', [Validators.required]],
    description: [''],
    roomTypeId: [''],
    baseRate: [0, [Validators.required, Validators.min(0)]],
    currency: ['USD', [Validators.required]],
    isActive: [true]
  });

  readonly calendarForm = this.formBuilder.nonNullable.group({
    ratePlanId: ['', [Validators.required]],
    date: ['', [Validators.required]],
    rateAmount: [0, [Validators.required, Validators.min(0)]],
    minStayNights: [1, [Validators.required, Validators.min(1)]],
    isClosed: [false]
  });

  readonly batchForm = this.formBuilder.nonNullable.group({
    ratePlanId: ['', [Validators.required]],
    startDate: ['', [Validators.required]],
    endDate: ['', [Validators.required]],
    rateAmount: [0, [Validators.required, Validators.min(0.01)]],
    minStayNights: [1, [Validators.min(1)]],
    onlyWeekends: [false]
  });

  readonly generateForm = this.formBuilder.nonNullable.group({
    ratePlanId: [''],
    startDate: [''],
    endDate: ['']
  });

  readonly seasonalForm = this.formBuilder.nonNullable.group({
    ratePlanId: ['', [Validators.required]],
    name: ['', [Validators.required]],
    startDate: ['', [Validators.required]],
    endDate: ['', [Validators.required]],
    priceOverride: [0, [Validators.required, Validators.min(0)]]
  });

  readonly promoForm = this.formBuilder.nonNullable.group({
    name: ['', [Validators.required]],
    description: [''],
    discountPercent: [10, [Validators.required, Validators.min(1), Validators.max(100)]],
    couponCount: [10, [Validators.required, Validators.min(1), Validators.max(1000)]],
    startDate: ['', [Validators.required]],
    endDate: ['', [Validators.required]],
    couponCode: [''],
    isActive: [true]
  });

  /* ── Form panel configuration ── */
  readonly formPanels = [
    {
      id: 'plan',
      label: 'Nuevo plan tarifario',
      icon: 'add_card',
      tooltip: 'Configura un plan tarifario base para la propiedad.'
    },
    {
      id: 'calendar',
      label: 'Actualizar tarifa',
      icon: 'edit_calendar',
      tooltip: 'Upsert por plan y fecha.'
    },
    {
      id: 'batch',
      label: 'Actualizar por lote',
      icon: 'date_range',
      tooltip: 'Aplica un precio a todo un rango de fechas.'
    },
    {
      id: 'generate',
      label: 'Generar calendario',
      icon: 'auto_awesome',
      tooltip: 'Genera entradas desde tarifa base y reglas de temporada.'
    },
    {
      id: 'seasonal',
      label: 'Regla de temporada',
      icon: 'event',
      tooltip: 'Define un precio override por rango de fechas.'
    },
    {
      id: 'promo',
      label: 'Promoción',
      icon: 'campaign',
      tooltip: 'Crea una campaña promocional con descuento y cupones.'
    }
  ] as const;

  readonly activeForm = signal<typeof this.formPanels[number]['id']>('plan');

  /* ── State ── */
  readonly editingPlan = signal<{ id: string; name: string; description: string; baseRate: number; currency: string; roomTypeId: string; isActive: boolean } | null>(null);
  readonly editingPromo = signal<{ campaignId: string; name: string; description: string; discountPercent: number; startDate: string; endDate: string; isActive: boolean } | null>(null);
  readonly deleteConfirm = signal<string | null>(null);
  readonly promoDeleteConfirm = signal<string | null>(null);
  readonly promotionsData = signal<{ campaigns: Array<any>; total: number } | null>(null);

  constructor() {
    this.route.queryParamMap
      .pipe(
        map((params) => Number(params.get('prop_id') ?? '0')),
        distinctUntilChanged(),
        switchMap((propId) => {
          this.viewState.set('loading');
          this.message.set('');
          this.errorMessage.set('');
          this.editingPlan.set(null);
          this.deleteConfirm.set(null);
          const load = propId > 0
            ? forkJoin({
                rates: this.api.getRates(propId),
                plans: this.api.getRatePlanOptions(propId)
              })
            : of(null);
          return load;
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (result) => {
          if (result) {
            this.viewModel.set(result.rates);
            this.ratePlanOptions.set(result.plans);
            this.selectedPropId.set(result.rates.propId);
            this.selectedLabel.set(result.rates.hotelLabel);
            this.viewState.set('success');
          } else {
            this.viewModel.set(null);
            this.ratePlanOptions.set([]);
            this.viewState.set('empty');
          }
        },
        error: () => this.viewState.set('error')
      });
  }

  get roomTypes() {
    return this.viewModel()?.roomTypes ?? [];
  }

  get seasonalRules() {
    return this.viewModel()?.seasonalRules ?? [];
  }

  onPropSelected(propId: number): void {
    void this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { prop_id: propId || null }
    });
  }

  createRatePlan() {
    const current = this.viewModel();
    if (!current || this.planForm.invalid) {
      this.planForm.markAllAsTouched();
      return;
    }

    const value = this.planForm.getRawValue();
    const obs = this.editingPlan()
      ? this.api.updateRatePlan(this.editingPlan()!.id, {
          name: value.name,
          description: value.description,
          baseRate: value.baseRate,
          currency: value.currency,
          roomTypeId: value.roomTypeId,
          isActive: value.isActive
        })
      : this.api.createRatePlan({
          propId: current.propId,
          name: value.name,
          description: value.description,
          baseRate: value.baseRate,
          currency: value.currency,
          roomTypeId: value.roomTypeId,
          isActive: value.isActive
        });
    obs
      .pipe(
        switchMap(() =>
          forkJoin({
            rates: this.api.getRates(current.propId),
            plans: this.api.getRatePlanOptions(current.propId)
          })
        ),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: ({ rates, plans }) => {
          this.viewModel.set(rates);
          this.ratePlanOptions.set(plans);
          this.message.set('Plan tarifario registrado');
          this.errorMessage.set('');
          this.editingPlan.set(null);
          this.planForm.reset({
            name: '',
            description: '',
            baseRate: 0,
            currency: 'USD',
            roomTypeId: '',
            isActive: true
          });
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible registrar el plan tarifario.');
          this.message.set('');
        }
      });
  }

  /** Pre-fill the plan form for editing. */
  onEditPlan(plan: import('../../models/rates.model').RatePlanItem) {
    this.editingPlan.set({
      id: plan.id,
      name: plan.name,
      description: plan.description,
      baseRate: plan.baseRate,
      currency: plan.currency,
      roomTypeId: plan.roomTypeId ?? '',
      isActive: plan.activeLabel === 'Sí'
    });
    this.planForm.patchValue({
      name: plan.name,
      description: plan.description,
      baseRate: plan.baseRate,
      currency: plan.currency,
      roomTypeId: plan.roomTypeId ?? '',
      isActive: plan.activeLabel === 'Sí'
    });
    // Scroll to form
    setTimeout(() => {
      document.querySelector('.form-grid')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
  }

  /** Cancel editing and reset form. */
  cancelEditPlan() {
    this.editingPlan.set(null);
    this.planForm.reset({
      name: '',
      description: '',
      baseRate: 0,
      currency: 'USD',
      roomTypeId: '',
      isActive: true
    });
  }

  /** Request delete confirmation. */
  onDeletePlan(planId: string) {
    this.deleteConfirm.set(planId);
  }

  /** Confirm and execute rate plan deletion. */
  confirmDeletePlan() {
    const planId = this.deleteConfirm();
    if (!planId) return;
    this.deleteConfirm.set(null);

    const current = this.viewModel();
    if (!current) return;

    this.api
      .deleteRatePlan(planId)
      .pipe(
        switchMap(() => this.api.getRates(current.propId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (rates) => {
          this.viewModel.set(rates);
          this.message.set('Plan tarifario eliminado');
          this.errorMessage.set('');
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'Error al eliminar plan.');
          this.message.set('');
        }
      });
  }

  saveRate() {
    const current = this.viewModel();
    if (!current || this.calendarForm.invalid) {
      this.calendarForm.markAllAsTouched();
      return;
    }

    const value = this.calendarForm.getRawValue();
    this.api
      .saveRate({
        propId: current.propId,
        ratePlanId: value.ratePlanId,
        date: value.date,
        rateAmount: value.rateAmount,
        minStayNights: value.minStayNights,
        isClosed: value.isClosed
      })
      .pipe(
        switchMap(() => this.api.getRates(current.propId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (rates) => {
          this.viewModel.set(rates);
          this.message.set('Tarifa actualizada');
          this.errorMessage.set('');
          this.calendarForm.reset({
            ratePlanId: '',
            date: '',
            rateAmount: 0,
            minStayNights: 1,
            isClosed: false
          });
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible actualizar la tarifa.');
          this.message.set('');
        }
      });
  }

  batchUpdateCalendar() {
    const current = this.viewModel();
    if (!current || this.batchForm.invalid) {
      this.batchForm.markAllAsTouched();
      return;
    }

    const value = this.batchForm.getRawValue();
    this.api
      .batchUpdateCalendar({
        propId: current.propId,
        ratePlanId: value.ratePlanId,
        startDate: value.startDate,
        endDate: value.endDate,
        rateAmount: value.rateAmount,
        minStayNights: value.minStayNights || undefined,
        onlyWeekends: value.onlyWeekends
      })
      .pipe(
        switchMap(() => this.api.getRates(current.propId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (rates) => {
          this.viewModel.set(rates);
          this.message.set('Calendario actualizado por lote');
          this.errorMessage.set('');
          this.batchForm.reset({
            ratePlanId: '',
            startDate: '',
            endDate: '',
            rateAmount: 0,
            minStayNights: 1,
            onlyWeekends: false
          });
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'Error al actualizar calendario por lote.');
          this.message.set('');
        }
      });
  }

  generateCalendar() {
    const current = this.viewModel();
    if (!current) return;

    const value = this.generateForm.getRawValue();
    this.api
      .generateCalendar({
        propId: current.propId,
        ratePlanId: value.ratePlanId || undefined,
        startDate: value.startDate || undefined,
        endDate: value.endDate || undefined
      })
      .pipe(
        switchMap((result) => {
          this.message.set(`Calendario generado: ${result.entries_generated} entradas`);
          return this.api.getRates(current.propId);
        }),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (rates) => {
          this.viewModel.set(rates);
          this.errorMessage.set('');
          this.generateForm.reset({
            ratePlanId: '',
            startDate: '',
            endDate: ''
          });
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'Error al generar calendario.');
          this.message.set('');
        }
      });
  }

  createSeasonalRule() {
    const current = this.viewModel();
    if (!current || this.seasonalForm.invalid) {
      this.seasonalForm.markAllAsTouched();
      return;
    }

    const value = this.seasonalForm.getRawValue();
    this.api
      .createSeasonalRule({
        propId: current.propId,
        ratePlanId: value.ratePlanId,
        name: value.name,
        startDate: value.startDate,
        endDate: value.endDate,
        priceOverride: value.priceOverride
      })
      .pipe(
        switchMap(() => this.api.getRates(current.propId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (rates) => {
          this.viewModel.set(rates);
          this.message.set('Regla de temporada creada');
          this.errorMessage.set('');
          this.seasonalForm.reset({
            ratePlanId: '',
            name: '',
            startDate: '',
            endDate: '',
            priceOverride: 0
          });
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'Error al crear regla de temporada.');
          this.message.set('');
        }
      });
  }

  deleteSeasonalRule(ruleId: string) {
    const current = this.viewModel();
    if (!current) return;

    this.api
      .deleteSeasonalRule(ruleId)
      .pipe(
        switchMap(() => this.api.getRates(current.propId)),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: (rates) => {
          this.viewModel.set(rates);
          this.message.set('Regla de temporada eliminada');
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'Error al eliminar regla de temporada.');
        }
      });
  }

  createPromotion() {
    const current = this.viewModel();
    if (!current || this.promoForm.invalid) {
      this.promoForm.markAllAsTouched();
      return;
    }

    const value = this.promoForm.getRawValue();
    const obs = this.editingPromo()
      ? this.api.updatePromotion(this.editingPromo()!.campaignId, {
          name: value.name,
          description: value.description,
          discountPercent: value.discountPercent,
          startDate: value.startDate,
          endDate: value.endDate,
          isActive: value.isActive
        })
      : this.api.createPromotion({
          propId: current.propId,
          name: value.name,
          description: value.description,
          discountPercent: value.discountPercent,
          startDate: value.startDate,
          endDate: value.endDate,
          couponCount: value.couponCount,
          couponCode: value.couponCode,
          isActive: value.isActive
        });
    obs
      .pipe(
        switchMap(() => forkJoin({
          rates: this.api.getRates(current.propId),
          plans: this.api.getRatePlanOptions(current.propId),
          promotions: this.api.listPropertyPromotions(current.propId)
        })),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: ({ rates, plans, promotions }) => {
          this.viewModel.set(rates);
          this.ratePlanOptions.set(plans);
          this.promotionsData.set(promotions);
          this.message.set(this.editingPromo() ? 'Promoción actualizada' : 'Promoción creada');
          this.errorMessage.set('');
          this.editingPromo.set(null);
          this.promoForm.reset({
            name: '',
            description: '',
            discountPercent: 10,
            couponCount: 10,
            startDate: '',
            endDate: '',
            couponCode: '',
            isActive: true
          });
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'No fue posible crear la promoción.');
          this.message.set('');
        }
      });
  }

  onEditPromo(promo: { campaignId: string; name: string; description: string; discountPercent: number; startDate: string; endDate: string; isActive: boolean }) {
    this.editingPromo.set(promo);
    this.promoForm.patchValue({
      name: promo.name,
      description: promo.description,
      discountPercent: promo.discountPercent,
      startDate: promo.startDate,
      endDate: promo.endDate,
      isActive: promo.isActive
    });
    setTimeout(() => {
      document.querySelector('.form-grid')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
  }

  cancelEditPromo() {
    this.editingPromo.set(null);
    this.promoForm.reset({
      name: '',
      description: '',
      discountPercent: 10,
      couponCount: 10,
      startDate: '',
      endDate: '',
      couponCode: '',
      isActive: true
    });
  }

  onTogglePromo(campaignId: string) {
    const current = this.viewModel();
    if (!current) return;

    this.api
      .togglePromotion(campaignId)
      .pipe(
        switchMap(() => forkJoin({
          rates: this.api.getRates(current.propId),
          plans: this.api.getRatePlanOptions(current.propId),
          promotions: this.api.listPropertyPromotions(current.propId)
        })),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: ({ rates, plans, promotions }) => {
          this.viewModel.set(rates);
          this.ratePlanOptions.set(plans);
          this.promotionsData.set(promotions);
          this.message.set('Estado de promoción actualizado');
          this.errorMessage.set('');
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'Error al cambiar estado.');
          this.message.set('');
        }
      });
  }

  onDeletePromo(campaignId: string) {
    this.promoDeleteConfirm.set(campaignId);
  }

  confirmDeletePromo() {
    const campaignId = this.promoDeleteConfirm();
    if (!campaignId) return;
    this.promoDeleteConfirm.set(null);

    const current = this.viewModel();
    if (!current) return;

    // Soft delete via update to inactive
    this.api
      .updatePromotion(campaignId, { isActive: false })
      .pipe(
        switchMap(() => forkJoin({
          rates: this.api.getRates(current.propId),
          promotions: this.api.listPropertyPromotions(current.propId)
        })),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe({
        next: ({ rates, promotions }) => {
          this.viewModel.set(rates);
          this.promotionsData.set(promotions);
          this.message.set('Promoción desactivada');
          this.errorMessage.set('');
        },
        error: (error: ApiError) => {
          this.errorMessage.set(error.message || 'Error al desactivar promoción.');
          this.message.set('');
        }
      });
  }

  get promotionsCampaigns() {
    const data = this.promotionsData();
    if (data) return data.campaigns;
    // Fallback to rates viewModel promotions
    return (this.viewModel()?.promotions ?? []).map((p) => ({
      campaign_id: p.campaignId,
      name: p.name,
      description: p.description,
      discount_percent: p.discountPercent,
      is_active: p.activeLabel === 'Sí',
      start_date: p.dateRange.split(' → ')[0] || '',
      end_date: p.dateRange.split(' → ')[1] || '',
      coupon_total: 0,
      coupon_used: 0,
      coupon_available: 0
    }));
  }
}
