import { CurrencyPipe, DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-rd-hero',
  standalone: true,
  imports: [CurrencyPipe, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="action-row">
      <a routerLink="/reservations" class="secondary-link">Volver</a>
      @if (canConfirm()) {
        <button type="button" class="btn-action btn-confirm" (click)="confirm.emit()" [disabled]="confirmPending()">
          <span class="material-symbols-outlined btn-icon">check_circle</span>
          {{ confirmPending() ? 'Confirmando...' : 'Confirmar reserva' }}
        </button>
        <button type="button" class="btn-action btn-reject" (click)="reject.emit()" [disabled]="rejectPending()">
          <span class="material-symbols-outlined btn-icon">cancel</span>
          {{ rejectPending() ? 'Rechazando...' : 'Rechazar reserva' }}
        </button>
      }
      @if (vm()?.canCancel && todayStr() < vm()!.checkInDate) {
        <button type="button" class="btn-action btn-cancel" (click)="cancel.emit()" [disabled]="cancelPending()">
          <span class="material-symbols-outlined btn-icon">block</span>
          Cancelar solicitud
        </button>
      }
      @if (canEdit() && !editMode()) {
        <button type="button" class="btn-action btn-edit" (click)="toggleEdit.emit()">
          <span class="material-symbols-outlined btn-icon">edit</span>
          Modificar
        </button>
      }
      @if (isStaff() && vm() && ['confirmed', 'checked_in'].includes(vm()!.status)) {
        <button type="button" class="btn-action btn-rooms" (click)="openRoomModal.emit()">
          <span class="material-symbols-outlined btn-icon">meeting_room</span>
          Asignar habitaciones
        </button>
      }
      @if (vm()?.status === 'checked_in') {
        <a [routerLink]="['/account/bookings', vm()!.bookingId, 'amenities']" class="btn-action btn-amenities">
          <span class="material-symbols-outlined btn-icon">spa</span>
          Solicitar amenities
        </a>
        <button type="button" class="btn-action btn-instay" (click)="goToInStay.emit(vm()!.bookingId)">
          <span class="material-symbols-outlined btn-icon">meeting_room</span>
          Mi Estancia
        </button>
      }
    </div>

    <section class="hero-grid">
      <article class="surface-card hero-card">
        <div class="hero-card-icon-wrap" style="--card-accent: var(--accent)">
          <span class="material-symbols-outlined">business</span>
        </div>
        <div class="hero-card-content">
          <span class="stat-label">Hotel</span>
          <strong>{{ vm()?.hotelLabel }}</strong>
        </div>
      </article>

      <article class="surface-card hero-card"
        [class.hero-status-pending]="vm()?.status === 'pending'"
        [class.hero-status-confirmed]="vm()?.status === 'confirmed'"
        [class.hero-status-checked-in]="vm()?.status === 'checked_in'"
        [class.hero-status-checked-out]="vm()?.status === 'checked_out'"
        [class.hero-status-cancelled]="vm()?.status === 'cancelled'"
        [class.hero-status-rejected]="vm()?.status === 'rejected'">
        <div class="hero-card-icon-wrap">
          @switch (vm()?.status) {
            @case ('pending') { <span class="material-symbols-outlined">pending</span> }
            @case ('confirmed') { <span class="material-symbols-outlined">check_circle</span> }
            @case ('checked_in') { <span class="material-symbols-outlined">vpn_key</span> }
            @case ('checked_out') { <span class="material-symbols-outlined">logout</span> }
            @case ('cancelled') { <span class="material-symbols-outlined">cancel</span> }
            @case ('rejected') { <span class="material-symbols-outlined">block</span> }
            @default { <span class="material-symbols-outlined">info</span> }
          }
        </div>
        <div class="hero-card-content">
          <span class="stat-label">Estado</span>
          <strong>
            @switch (vm()?.status) {
              @case ('pending') { Pendiente }
              @case ('confirmed') { Confirmada }
              @case ('checked_in') { Checked-In }
              @case ('checked_out') { Checked-Out }
              @case ('cancelled') { Cancelada }
              @case ('rejected') { Rechazada }
              @default { {{ vm()?.status }} }
            }
          </strong>
        </div>
      </article>

      <article class="surface-card hero-card">
        <div class="hero-card-icon-wrap" style="--card-accent: #a78bfa">
          <span class="material-symbols-outlined">language</span>
        </div>
        <div class="hero-card-content">
          <span class="stat-label">Origen</span>
          <strong>
            @switch (vm()?.bookingSource) {
              @case ('angular_api') { Plataforma Web }
              @case ('manual_partner') { Reserva Manual Partner }
              @case ('reception_physical') { Recepción Física }
              @case ('manual') { Registro Manual }
              @default { {{ vm()?.bookingSource }} }
            }
          </strong>
        </div>
      </article>

      @if (vm()?.totalPrice !== null) {
        <article class="surface-card hero-card">
          <div class="hero-card-icon-wrap" style="--card-accent: var(--success)">
            <span class="material-symbols-outlined">payments</span>
          </div>
          <div class="hero-card-content">
            <span class="stat-label">Total</span>
            <strong>
              @if (vm()?.discountPercent) {
                <span style="text-decoration: line-through; opacity: 0.7; font-weight: normal; margin-right: 4px; font-size: 0.9em;">{{ vm()?.originalTotalPrice | currency:vm()?.currency }}</span>
                {{ vm()?.totalPrice | currency:vm()?.currency }} <span style="font-size: 0.8em; font-weight: normal;">(-{{ vm()?.discountPercent }}%)</span>
              } @else {
                {{ vm()?.totalPrice | currency:vm()?.currency }}
              }
            </strong>
          </div>
        </article>
      }

      @if ((vm()?.amenitiesCount ?? 0) > 0) {
        <article class="surface-card hero-card">
          <div class="hero-card-icon-wrap" style="--card-accent: #f59e0b">
            <span class="material-symbols-outlined">spa</span>
          </div>
          <div class="hero-card-content">
            <span class="stat-label">Amenities solicitados</span>
            <strong>{{ vm()?.amenitiesCount }} {{ vm()?.amenitiesCount === 1 ? 'servicio' : 'servicios' }}</strong>
            @if ((vm()?.amenitiesTotal ?? 0) > 0) {
              <span class="hero-card-sub">{{ vm()?.amenitiesTotal | currency:'USD' }}</span>
            }
          </div>
        </article>
      }
    </section>
  `
})
export class RdHeroComponent {
  readonly vm = input<any>(null);
  readonly todayStr = input<string>('');
  readonly canConfirm = input<boolean>(false);
  readonly canEdit = input<boolean>(false);
  readonly isStaff = input<boolean>(false);
  readonly editMode = input<boolean>(false);
  readonly cancelPending = input<boolean>(false);
  readonly confirmPending = input<boolean>(false);
  readonly rejectPending = input<boolean>(false);

  readonly confirm = output<void>();
  readonly reject = output<void>();
  readonly cancel = output<void>();
  readonly toggleEdit = output<void>();
  readonly openRoomModal = output<void>();
  readonly goToInStay = output<string>();
}
