import { ChangeDetectionStrategy, Component, inject, input, output } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import type { AvailabilityBulkEdit } from '../../models/availability.model';

@Component({
  selector: 'app-bulk-edit-panel',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './bulk-edit-panel.html',
  styleUrl: './bulk-edit-panel.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BulkEditPanelComponent {
  private readonly formBuilder = inject(FormBuilder);

  readonly startDate = input.required<string>();
  readonly endDate = input.required<string>();
  readonly applyBulk = output<AvailabilityBulkEdit>();

  readonly form = this.formBuilder.group({
    startDate: [''],
    endDate: [''],
    totalRooms: [''],
    availableRooms: [''],
    blockedRooms: [''],
    rateAmount: [''],
    minStayNights: [''],
    closedMode: ['keep'],
  });

  constructor() {
    this.form.patchValue({ closedMode: 'keep' });
  }

  ngOnChanges() {
    this.form.patchValue({
      startDate: this.startDate(),
      endDate: this.endDate(),
    });
  }

  submit() {
    const raw = this.form.getRawValue();
    this.applyBulk.emit({
      startDate: raw.startDate || this.startDate(),
      endDate: raw.endDate || this.endDate(),
      totalRooms: raw.totalRooms === '' ? null : Number(raw.totalRooms),
      availableRooms: raw.availableRooms === '' ? null : Number(raw.availableRooms),
      blockedRooms: raw.blockedRooms === '' ? null : Number(raw.blockedRooms),
      rateAmount: raw.rateAmount === '' ? null : Number(raw.rateAmount),
      minStayNights: raw.minStayNights === '' ? null : Number(raw.minStayNights),
      closedMode: (raw.closedMode as AvailabilityBulkEdit['closedMode']) || 'keep',
    });
  }
}
