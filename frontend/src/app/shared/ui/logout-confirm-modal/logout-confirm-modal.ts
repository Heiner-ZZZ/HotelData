import { ChangeDetectionStrategy, Component, HostListener, input, output } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';

import type {
  LogoutGuardResponse,
  OpenAttendanceShift,
  OpenCashShift,
} from '../../services/logout-guard.service';

@Component({
  selector: 'app-logout-confirm-modal',
  imports: [DatePipe, RouterLink],
  templateUrl: './logout-confirm-modal.html',
  styleUrl: './logout-confirm-modal.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LogoutConfirmModalComponent {
  readonly data = input<LogoutGuardResponse | null>(null);

  /** User confirmed: log out anyway. */
  readonly proceed = output<void>();
  /** User changed their mind: stay in the session. */
  readonly cancel = output<void>();

  readonly cashShiftLink = (shift: OpenCashShift): string[] =>
    ['/management/shifts/dashboard'];

  readonly cashShiftQueryParams = (shift: OpenCashShift): Record<string, string> => ({
    prop_id: String(shift.prop_id),
  });

  readonly attendanceLink = (att: OpenAttendanceShift): string[] =>
    ['/management/hr/portal', att.employee_id];

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.cancel.emit();
  }
}
