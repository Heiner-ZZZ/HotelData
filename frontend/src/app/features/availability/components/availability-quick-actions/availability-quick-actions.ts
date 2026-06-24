import { ChangeDetectionStrategy, Component, input, output, ViewEncapsulation } from '@angular/core';

@Component({
  selector: 'app-availability-quick-actions',
  imports: [],
  templateUrl: './availability-quick-actions.html',
  styleUrl: '../../pages/availability-page/availability-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
})
export class AvailabilityQuickActionsComponent {
  readonly selectionCount = input(0);
  readonly selectionSummary = input('');
  readonly multiSelectMode = input(false);
  readonly activeCell = input<{ date: string; roomTypeName: string } | null>(null);
  readonly saving = input(false);
  readonly batchAvailableValue = input(0);

  readonly batchMarkUnavailable = output<void>();
  readonly blockSelectedRange = output<void>();
  readonly clearSelectionOutput = output<void>();
  readonly selectAllCells = output<void>();
  readonly quickBlock = output<void>();
  readonly quickMarkUnavailable = output<void>();
  readonly batchAvailableChange = output<number>();
  readonly dismissActiveCell = output<void>();

  onBatchMark() { this.batchMarkUnavailable.emit(); }
  onBlockRange() { this.blockSelectedRange.emit(); }
  onClearSelection() { this.clearSelectionOutput.emit(); }
  onSelectAll() { this.selectAllCells.emit(); }
  onQuickBlock() { this.quickBlock.emit(); }
  onQuickMarkUnavailable() { this.quickMarkUnavailable.emit(); }
  onDismiss() { this.dismissActiveCell.emit(); }

  activeCellLabel(): string {
    const cell = this.activeCell();
    if (!cell) return '';
    return `${cell.date} — ${cell.roomTypeName}`;
  }
}
