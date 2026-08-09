import { ChangeDetectionStrategy, Component, input, output, signal } from '@angular/core';

export interface SeasonalRuleRow {
  ruleId: string;
  name: string;
  ratePlanId: string;
  startDate: string;
  endDate: string;
  rangeLabel: string;
  priceOverride: number;
}

@Component({
  selector: 'app-seasonal-rules-table',
  imports: [],
  templateUrl: './seasonal-rules-table.html',
  styleUrl: './seasonal-rules-table.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SeasonalRulesTableComponent {
  readonly rules = input<SeasonalRuleRow[]>([]);
  readonly editRule = output<SeasonalRuleRow>();
  readonly deleteRule = output<string>();

  /**
   * Regla armada para borrar: el delete es un hard delete sin confirmación
   * previa del backend, así que el borrado NO se emite al primer click — se
   * arma aquí y solo se confirma con `confirmDelete()`. El alert role="alert"
   * del template es el que avisa antes de la acción destructiva.
   */
  readonly deleteConfirm = signal<SeasonalRuleRow | null>(null);

  requestDelete(rule: SeasonalRuleRow): void {
    this.deleteConfirm.set(rule);
  }

  cancelDelete(): void {
    this.deleteConfirm.set(null);
  }

  confirmDelete(): void {
    const rule = this.deleteConfirm();
    if (!rule) return;
    this.deleteConfirm.set(null);
    this.deleteRule.emit(rule.ruleId);
  }
}
