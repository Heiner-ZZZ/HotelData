import { CurrencyPipe, DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { httpResource } from '@angular/common/http';
import { RouterLink } from '@angular/router';

import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';

interface HotelFinancialAggregate {
  prop_id: number;
  rebuilt_at: string;
  reconciliation_status: 'ok' | 'warning';
  guest_ar: {
    invoiced: number;
    collected: number;
    refunded: number;
    net_collected: number;
    outstanding_folios: number;
    confirmed_payment_count: number;
    refunded_payment_count: number;
  };
  operations: { maintenance_cost: number };
  vendor_ap: { approved: number; paid: number; unpaid: number };
  general_ledger: {
    debit: number;
    credit: number;
    difference: number;
    is_balanced: boolean;
    transaction_count: number;
  };
  event_counts: Record<string, number>;
  source_counts: Record<string, number>;
}

@Component({
  selector: 'app-financial-control-page',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, RouterLink, PageHeaderComponent, LoadingStateComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page-wrap financial-control-page">
      <app-page-header
        eyebrow="Control hotel-scoped"
        title="Control financiero del hotel"
        description="Guest AR, operaciones, Vendor AP y libro mayor conectados por eventos idempotentes."
      />

      <div class="actions-row">
        <button class="btn btn--primary" type="button" (click)="rebuild()" [disabled]="busy() || !propId()">
          <span class="material-symbols-outlined icon">sync</span> Reconstruir agregado
        </button>
        <button class="btn" type="button" (click)="backfill()" [disabled]="busy() || !propId()">
          <span class="material-symbols-outlined icon">history</span> Proyectar eventos históricos
        </button>
        <a class="btn btn--secondary" [routerLink]="['/management/billing/folios']">
          <span class="material-symbols-outlined icon">receipt_long</span> Resolver folios
        </a>
      </div>

      @if (message(); as text) {
        <div class="control-message">{{ text }}</div>
      }

      @switch (viewState()) {
        @case ('loading') { <app-loading-state label="Cargando control financiero..." /> }
        @case ('error') {
          <div class="control-empty">
            <span class="material-symbols-outlined">account_balance</span>
            <strong>No hay agregado reconstruido para este hotel.</strong>
            <p>Ejecuta “Reconstruir agregado” para crear la proyección desde Mongo.</p>
          </div>
        }
        @default {
          @if (aggregate(); as a) {
            <div class="control-status" [class.warning]="a.reconciliation_status !== 'ok'">
              <span class="material-symbols-outlined">{{ a.reconciliation_status === 'ok' ? 'check_circle' : 'warning' }}</span>
              {{ a.reconciliation_status === 'ok' ? 'Agregado consistente en partida doble' : 'Requiere revisión de conciliación' }}
              <span class="control-status__meta">Hotel #{{ a.prop_id }} · actualizado {{ a.rebuilt_at | date:'dd/MM/yyyy HH:mm' }}</span>
            </div>

            <div class="control-grid">
              <section class="control-card control-card--blue">
                <div class="control-card__title"><span class="material-symbols-outlined">payments</span> Guest AR</div>
                <div class="control-card__value">{{ a.guest_ar.invoiced | currency:'MXN':'symbol-narrow':'1.2-2' }}</div>
                <dl>
                  <div><dt>Cobrado bruto</dt><dd>{{ a.guest_ar.collected | currency:'MXN':'symbol-narrow':'1.2-2' }}</dd></div>
                  <div><dt>Reembolsado</dt><dd>{{ a.guest_ar.refunded | currency:'MXN':'symbol-narrow':'1.2-2' }}</dd></div>
                  <div><dt>Cobro neto</dt><dd>{{ a.guest_ar.net_collected | currency:'MXN':'symbol-narrow':'1.2-2' }}</dd></div>
                  <div><dt>Folios pendientes</dt><dd>{{ a.guest_ar.outstanding_folios | currency:'MXN':'symbol-narrow':'1.2-2' }}</dd></div>
                  <div><dt>Pagos confirmados</dt><dd>{{ a.guest_ar.confirmed_payment_count }}</dd></div>
                </dl>
              </section>

              <section class="control-card control-card--amber">
                <div class="control-card__title"><span class="material-symbols-outlined">home_repair_service</span> Operaciones</div>
                <div class="control-card__value">{{ a.operations.maintenance_cost | currency:'MXN':'symbol-narrow':'1.2-2' }}</div>
                <dl><div><dt>Coste de mantenimiento</dt><dd>Real registrado</dd></div></dl>
              </section>

              <section class="control-card control-card--red">
                <div class="control-card__title"><span class="material-symbols-outlined">store</span> Vendor AP</div>
                <div class="control-card__value">{{ a.vendor_ap.approved | currency:'MXN':'symbol-narrow':'1.2-2' }}</div>
                <dl>
                  <div><dt>Pagado</dt><dd>{{ a.vendor_ap.paid | currency:'MXN':'symbol-narrow':'1.2-2' }}</dd></div>
                  <div><dt>Pendiente</dt><dd>{{ a.vendor_ap.unpaid | currency:'MXN':'symbol-narrow':'1.2-2' }}</dd></div>
                </dl>
              </section>

              <section class="control-card control-card--green">
                <div class="control-card__title"><span class="material-symbols-outlined">account_balance</span> Libro mayor</div>
                <div class="control-card__value">{{ a.general_ledger.debit | currency:'MXN':'symbol-narrow':'1.2-2' }}</div>
                <dl>
                  <div><dt>Créditos</dt><dd>{{ a.general_ledger.credit | currency:'MXN':'symbol-narrow':'1.2-2' }}</dd></div>
                  <div><dt>Diferencia</dt><dd>{{ a.general_ledger.difference | currency:'MXN':'symbol-narrow':'1.2-2' }}</dd></div>
                  <div><dt>Movimientos</dt><dd>{{ a.general_ledger.transaction_count }}</dd></div>
                </dl>
              </section>
            </div>

            <section class="control-card control-events">
              <div class="control-card__title"><span class="material-symbols-outlined">hub</span> Eventos canónicos por dominio</div>
              <div class="event-chips">
                @for (entry of eventEntries(a); track entry[0]) {
                  <span class="event-chip"><strong>{{ entry[0] }}</strong> {{ entry[1] }}</span>
                } @empty {
                  <span class="muted">Aún no hay eventos; proyecta los documentos históricos.</span>
                }
              </div>
            </section>
          }
        }
      }
    </div>
  `,
  styles: [`
    .financial-control-page { --control-border: color-mix(in srgb, var(--outline, #cbd5e1) 55%, transparent); }
    .actions-row { display: flex; flex-wrap: wrap; gap: .65rem; margin: 1rem 0; }
    .control-message { margin: .75rem 0; padding: .75rem 1rem; border-radius: .6rem; background: color-mix(in srgb, var(--primary, #2563eb) 10%, transparent); }
    .control-status { display: flex; align-items: center; gap: .5rem; margin: 1rem 0; padding: .8rem 1rem; border: 1px solid #86efac; border-radius: .7rem; color: #166534; background: #f0fdf4; }
    .control-status.warning { border-color: #fbbf24; color: #92400e; background: #fffbeb; }
    .control-status__meta { margin-left: auto; font-size: .8rem; opacity: .75; }
    .control-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 1rem; }
    .control-card { padding: 1rem; border: 1px solid var(--control-border); border-radius: .8rem; background: var(--surface, #fff); box-shadow: 0 2px 8px rgba(15, 23, 42, .04); }
    .control-card--blue { border-top: 3px solid #2563eb; } .control-card--amber { border-top: 3px solid #d97706; } .control-card--red { border-top: 3px solid #dc2626; } .control-card--green { border-top: 3px solid #059669; }
    .control-card__title { display: flex; align-items: center; gap: .4rem; font-weight: 700; }
    .control-card__value { margin: 1rem 0; font-size: 1.45rem; font-weight: 800; }
    dl { display: grid; gap: .45rem; margin: 0; } dl div { display: flex; justify-content: space-between; gap: .5rem; font-size: .83rem; } dt { color: var(--muted-text, #64748b); } dd { margin: 0; font-weight: 650; text-align: right; }
    .control-events { margin-top: 1rem; } .event-chips { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: .8rem; } .event-chip { padding: .4rem .6rem; border-radius: 999px; background: color-mix(in srgb, var(--primary, #2563eb) 9%, transparent); font-size: .78rem; } .event-chip strong { margin-right: .25rem; } .muted { color: var(--muted-text, #64748b); }
    .control-empty { display: grid; place-items: center; gap: .5rem; min-height: 240px; padding: 2rem; border: 1px dashed var(--control-border); border-radius: .8rem; text-align: center; color: var(--muted-text, #64748b); }
    @media (max-width: 1000px) { .control-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .control-status__meta { margin-left: 0; } .control-status { flex-wrap: wrap; } }
    @media (max-width: 600px) { .control-grid { grid-template-columns: 1fr; } }
  `],
})
export class FinancialControlPageComponent {
  private readonly http = inject(HttpClient);
  private readonly propertyContext = inject(PropertyContextService);

  readonly propId = this.propertyContext.currentPropId;
  readonly message = signal<string | null>(null);
  readonly busy = signal(false);
  readonly resource = httpResource<HotelFinancialAggregate>(() => {
    const propId = this.propId();
    return propId > 0 ? `/api/hotels/${propId}/reconciliation/aggregate` : undefined;
  });
  readonly aggregate = computed(() => this.resource.value() ?? null);
  readonly viewState = computed(() => {
    if (this.resource.isLoading()) return 'loading' as const;
    if (this.resource.error()) return 'error' as const;
    return this.aggregate() ? 'success' as const : 'error' as const;
  });

  eventEntries(aggregate: HotelFinancialAggregate): [string, number][] {
    return Object.entries(aggregate.event_counts ?? {}).sort((a, b) => b[1] - a[1]);
  }

  rebuild(): void {
    const propId = this.propId();
    if (!propId) return;
    this.runAction(`/api/hotels/${propId}/reconciliation/aggregate/rebuild`, 'Agregado reconstruido desde las fuentes del hotel.');
  }

  backfill(): void {
    const propId = this.propId();
    if (!propId) return;
    this.runAction(`/api/hotels/${propId}/reconciliation/events/backfill`, 'Eventos históricos proyectados de forma idempotente.');
  }

  private runAction(url: string, message: string): void {
    this.busy.set(true);
    this.message.set(null);
    this.http.post(url, {}, { withCredentials: true }).subscribe({
      next: () => { this.message.set(message); this.resource.reload(); this.busy.set(false); },
      error: () => { this.message.set('No se pudo actualizar el control financiero.'); this.busy.set(false); },
    });
  }
}
