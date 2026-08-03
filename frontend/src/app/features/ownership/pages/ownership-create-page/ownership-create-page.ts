import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { debounceTime, distinctUntilChanged, switchMap, tap } from 'rxjs';

import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ApiError } from '../../../../core/api/api-error.model';
import { OperationModeService } from '../../../../core/services/operation-mode.service';
import { OwnershipApiService } from '../../services/ownership-api.service';
import type { OwnershipRole, HotelSearchResult } from '../../models/ownership.model';

@Component({
  selector: 'app-ownership-create-page',
  imports: [PageHeaderComponent, ReactiveFormsModule, RouterLink],
  templateUrl: './ownership-create-page.html',
  styleUrl: './ownership-create-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class OwnershipCreatePageComponent {
  private readonly api = inject(OwnershipApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);
  private readonly operationMode = inject(OperationModeService);

  readonly roles = signal<OwnershipRole[]>([]);
  readonly submitting = signal(false);
  readonly errorMessage = signal('');

  readonly searchControl = new FormControl('');
  readonly searching = signal(false);
  readonly searchResults = signal<HotelSearchResult[]>([]);
  readonly selectedHotels = signal<HotelSearchResult[]>([]);

  readonly form = new FormGroup({
    username: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    email: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.email] }),
    displayName: new FormControl('', { nonNullable: true }),
    password: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.minLength(6)] }),
    primaryRole: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
  });

  constructor() {
    // Página de creación → modo INSERT en el nav (ámbar: registra información nueva)
    this.operationMode.setMode('insert', 'Propietario');
    this.destroyRef.onDestroy(() => this.operationMode.reset());

    this.api.getRoles().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (roles) => this.roles.set(roles),
      error: () => {
        this.errorMessage.set('No fue posible cargar los roles disponibles.');
      }
    });

    this.searchControl.valueChanges.pipe(
      debounceTime(350),
      distinctUntilChanged(),
      tap(() => this.searching.set(true)),
      switchMap((q) => this.api.searchHotels(q || '', 1, 15)),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (result) => {
        this.searchResults.set(result.items);
        this.searching.set(false);
      },
      error: () => {
        this.searchResults.set([]);
        this.searching.set(false);
      }
    });
  }

  isSelected(propId: number): boolean {
    return this.selectedHotels().some(h => h.propId === propId);
  }

  addHotel(hotel: HotelSearchResult) {
    if (!this.isSelected(hotel.propId)) {
      this.selectedHotels.update(list => [...list, hotel]);
    }
  }

  removeHotel(propId: number) {
    this.selectedHotels.update(list => list.filter(h => h.propId !== propId));
  }

  onSubmit() {
    if (this.form.invalid || this.submitting()) return;
    this.submitting.set(true);
    this.errorMessage.set('');

    const { username, email, displayName, password, primaryRole } = this.form.getRawValue();

    this.api.createUser({
      username,
      email,
      password,
      primary_role: primaryRole,
      display_name: displayName || username,
      assigned_hotels: this.selectedHotels().map(h => h.propId)
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (result) => {
        this.submitting.set(false);
        if (result.ok) {
          void this.router.navigate(['/ownership/users']);
        } else {
          this.errorMessage.set(result.message);
        }
      },
      error: (err: ApiError) => {
        this.submitting.set(false);
        this.errorMessage.set(err.message || 'Error al crear usuario.');
      }
    });
  }
}
