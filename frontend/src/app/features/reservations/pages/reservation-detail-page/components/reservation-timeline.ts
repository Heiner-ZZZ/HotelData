import { ChangeDetectionStrategy, Component, computed, DestroyRef, inject, input, output, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { LoadingStateComponent } from '../../../../../shared/ui/loading-state/loading-state';
import type { ReservationDetailViewModel } from '../../../models/reservations.model';
import { ReservationsApiService } from '../../../services/reservations-api.service';

interface RoomGuestEntry {
  roomIndex: number;
  guests: { guestName: string; guestEmail: string; guestPhone: string; age: number | null; isChild: boolean; isPrimaryForRoom: boolean }[];
}

@Component({
  selector: 'app-reservation-timeline',
  imports: [FormsModule, LoadingStateComponent],
  templateUrl: './reservation-timeline.html',
  styleUrl: './reservation-timeline.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ReservationTimelineComponent {
  private readonly destroyRef = inject(DestroyRef);
  private readonly reservationsApi = inject(ReservationsApiService);

  readonly reservation = input.required<ReservationDetailViewModel>();
  readonly isStaff = input(false);
  readonly successMessage = output<string>();

  readonly roomGuests = signal<RoomGuestEntry[]>([]);
  readonly guestsLoading = signal(false);
  readonly guestsSaving = signal(false);
  readonly guestsEditMode = signal(false);

  readonly reviewSuccess = signal(false);
  readonly reviewForm = signal({ rating: 0, title: '', comment: '' });
  readonly reviewSubmitting = signal(false);

  readonly showReviewForm = computed(() => {
    const vm = this.reservation();
    const isCompleted =
      vm.status === 'checked_out' || vm.stayStatus === 'checked_out' ||
      vm.status === 'completed' || vm.stayStatus === 'completed';
    return isCompleted && !this.reviewSuccess() && !this.isStaff();
  });

  readonly totalRooms = computed(() => this.reservation().rooms || 1);

  readonly canManageGuests = computed(() => {
    const vm = this.reservation();
    return vm.status === 'confirmed' && vm.rooms > 0;
  });

  // ── Guest management ──

  loadRoomGuests() {
    const vm = this.reservation();
    this.guestsLoading.set(true);
    this.reservationsApi.getRoomGuests(vm.bookingId)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (items: any[]) => {
          const entries: RoomGuestEntry[] = items.map((item: any) => ({
            roomIndex: item.room_index,
            guests: (item.guests || []).map((g: any) => ({
              guestName: g.guest_name || '',
              guestEmail: g.guest_email || '',
              guestPhone: g.guest_phone || '',
              age: g.age ?? null,
              isChild: !!g.is_child,
              isPrimaryForRoom: !!g.is_primary_for_room,
            })),
          }));
          this.roomGuests.set(entries);
          this.guestsLoading.set(false);
        },
        error: () => this.guestsLoading.set(false),
      });
  }

  enterGuestsMode() {
    this.guestsEditMode.set(true);
    this.loadRoomGuests();
  }

  cancelGuestEdit() {
    this.guestsEditMode.set(false);
    this.roomGuests.set([]);
  }

  getRoomGuestsForIndex(idx: number): RoomGuestEntry {
    const existing = this.roomGuests().find((r) => r.roomIndex === idx);
    return existing || { roomIndex: idx, guests: [] };
  }

  addGuestToRoom(roomIndex: number) {
    this.roomGuests.update((list) => {
      const copy = [...list];
      const idx = copy.findIndex((r) => r.roomIndex === roomIndex);
      if (idx >= 0) {
        copy[idx] = {
          ...copy[idx],
          guests: [...copy[idx].guests, { guestName: '', guestEmail: '', guestPhone: '', age: null, isChild: false, isPrimaryForRoom: copy[idx].guests.length === 0 }],
        };
      } else {
        copy.push({ roomIndex, guests: [{ guestName: '', guestEmail: '', guestPhone: '', age: null, isChild: false, isPrimaryForRoom: true }] });
      }
      return copy;
    });
  }

  removeGuestFromRoom(roomIndex: number, guestIdx: number) {
    this.roomGuests.update((list) => {
      const copy = [...list];
      const idx = copy.findIndex((r) => r.roomIndex === roomIndex);
      if (idx >= 0) {
        const guests = [...copy[idx].guests];
        guests.splice(guestIdx, 1);
        copy[idx] = { ...copy[idx], guests };
      }
      return copy;
    });
  }

  updateGuestField(roomIndex: number, guestIdx: number, field: string, value: any) {
    this.roomGuests.update((list) => {
      const copy = [...list];
      const idx = copy.findIndex((r) => r.roomIndex === roomIndex);
      if (idx >= 0) {
        const guests = [...copy[idx].guests];
        guests[guestIdx] = { ...guests[guestIdx], [field]: value };
        copy[idx] = { ...copy[idx], guests };
      }
      return copy;
    });
  }

  saveRoomGuests() {
    const vm = this.reservation();
    if (this.guestsSaving()) return;
    this.guestsSaving.set(true);
    const payload = this.roomGuests().map((entry) => ({
      room_index: entry.roomIndex,
      guests: entry.guests.map((g) => ({
        guest_name: g.guestName,
        guest_email: g.guestEmail,
        guest_phone: g.guestPhone,
        age: g.age,
        is_child: g.isChild,
        is_primary_for_room: g.isPrimaryForRoom,
      })),
    }));
    this.reservationsApi.saveRoomGuests(vm.bookingId, payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.guestsSaving.set(false);
          this.guestsEditMode.set(false);
          this.roomGuests.set([]);
          this.successMessage.emit('Datos de huéspedes guardados correctamente.');
        },
        error: () => this.guestsSaving.set(false),
      });
  }

  parseAge(value: string): number | null {
    const n = parseInt(value, 10);
    return isNaN(n) ? null : n;
  }

  // ── Review form ──

  setReviewRating(rating: number) {
    this.reviewForm.update((f) => ({ ...f, rating }));
  }

  submitReview() {
    const vm = this.reservation();
    if (this.reviewSubmitting()) return;
    const f = this.reviewForm();
    if (f.rating === 0) return;

    this.reviewSubmitting.set(true);
    this.reservationsApi.createGuestReview(vm.bookingId, vm.propId, f.rating, f.title, f.comment)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.reviewSubmitting.set(false);
          this.reviewSuccess.set(true);
          this.successMessage.emit('¡Gracias por tu reseña!');
        },
        error: () => this.reviewSubmitting.set(false),
      });
  }
}
