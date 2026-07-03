import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { DatePipe } from '@angular/common';
import { switchMap, timer, map, BehaviorSubject } from 'rxjs';

import { HrApiService } from '../../services/hr-api.service';
import type { EmployeePortal } from '../../models/hr.model';

@Component({
  selector: 'app-employee-dashboard-page',
  standalone: true,
  imports: [DatePipe],
  templateUrl: './employee-dashboard-page.html',
  styleUrl: './employee-dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class EmployeeDashboardPageComponent {
  private readonly api = inject(HrApiService);
  private readonly route = inject(ActivatedRoute);

  private readonly refresh$ = new BehaviorSubject<void>(undefined);

  readonly currentTime = toSignal(
    timer(0, 1000).pipe(map(() => {
      const now = new Date();
      return now.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit', hour12: true });
    })), { initialValue: '' }
  );

  readonly currentDate = toSignal(
    timer(0, 60000).pipe(map(() => {
      return new Date().toLocaleDateString('es-MX', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    })), { initialValue: '' }
  );

  readonly portal = toSignal(
    this.refresh$.pipe(
      switchMap(() => this.route.paramMap),
      switchMap(params => {
        const employeeId = params.get('employeeId') || '';
        return this.api.getPortal(employeeId);
      })
    )
  );

  readonly shiftLoading = signal(false);

  doCheckIn() {
    const data = this.portal();
    if (!data?.currentShift) return;

    this.shiftLoading.set(true);
    const employeeId = data.employee.id;
    const shift = data.currentShift;
    const action = shift.status === 'active'
      ? this.api.shiftCheckOut(shift.id, employeeId)
      : this.api.shiftCheckIn(shift.id, employeeId);

    action.subscribe({
      next: () => {
        this.shiftLoading.set(false);
        this.refresh$.next();
      },
      error: () => this.shiftLoading.set(false),
    });
  }
}
