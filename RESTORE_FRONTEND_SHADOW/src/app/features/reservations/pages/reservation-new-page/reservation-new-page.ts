import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { map } from 'rxjs';

import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';
import type { ReservationOptionsViewModel } from '../../models/reservations.model';
import { ReservationsApiService } from '../../services/reservations-api.service';

@Component({
  selector: 'app-reservation-new-page',
  standalone: true,
  imports: [ErrorStateComponent, LoadingStateComponent, PageHeaderComponent, ReactiveFormsModule, RouterLink],
  templateUrl: './reservation-new-page.html',
  styleUrl: './reservation-new-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ReservationNewPageComponent {
  private readonly api = inject(ReservationsApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly formBuilder = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  readonly viewState = signal<ViewState>('loading');
  readonly optionsViewModel = signal<ReservationOptionsViewModel | null>(null);
  readonly submitError = signal('');

  readonly form = this.formBuilder.nonNullable.group({
    propId: ['', Validators.required],
    guestName: ['', Validators.required],
    guestEmail: ['', [Validators.required, Validators.email]],
    checkInDate: ['', Validators.required],
    checkOutDate: ['', Validators.required],
    adults: [2, [Validators.required, Validators.min(1)]],
    children: [0, [Validators.required, Validators.min(0)]],
    rooms: [1, [Validators.required, Validators.min(1)]],
    comment: ['']
  });

  constructor() {
    this.route.queryParamMap
      .pipe(
        map((params) => Number(params.get('prop_id') ?? '') || undefined),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe((propId) => this.load(propId));
  }

  submit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.submitError.set('');
    const raw = this.form.getRawValue();
    this.api
      .createReservation({
        prop_id: Number(raw.propId),
        guest_name: raw.guestName,
        guest_email: raw.guestEmail,
        check_in_date: raw.checkInDate,
        check_out_date: raw.checkOutDate,
        adults: raw.adults,
        children: raw.children,
        rooms: raw.rooms,
        comment: raw.comment
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => void this.router.navigate([this.detailBaseRoute(), result.booking_id]),
        error: (error: { message?: string }) => {
          this.submitError.set(error.message || 'No se pudo crear la solicitud.');
        }
      });
  }

  backRoute() {
    return this.isAccountContext() ? '/account/bookings' : '/management/reservations';
  }

  private load(propId?: number) {
    this.viewState.set('loading');
    this.api
      .getReservationOptions(propId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (vm) => {
          this.optionsViewModel.set(vm);
          this.form.reset({
            propId: vm.defaults.propId,
            guestName: vm.defaults.guestName,
            guestEmail: vm.defaults.guestEmail,
            checkInDate: vm.defaults.checkInDate,
            checkOutDate: vm.defaults.checkOutDate,
            adults: vm.defaults.adults,
            children: vm.defaults.children,
            rooms: vm.defaults.rooms,
            comment: vm.defaults.comment
          });
          this.viewState.set('success');
        },
        error: () => this.viewState.set('error')
      });
  }

  private detailBaseRoute() {
    return this.isAccountContext() ? '/account/bookings' : '/management/reservations';
  }

  private isAccountContext() {
    return this.router.url.startsWith('/account');
  }
}
