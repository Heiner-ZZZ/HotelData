import { RouterLink } from '@angular/router';
import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-rp-kpi-grid',
  standalone: true,
  imports: [RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="kpi-grid">
      <article class="kpi-card">
        <div class="kpi-icon-wrap" style="--card-accent: var(--accent)">
          <span class="material-symbols-outlined kpi-icon">business</span>
        </div>
        <div class="kpi-body">
          <p class="kpi-label">Hotel</p>
          <h3 class="kpi-value">{{ vm()?.hotelName }}</h3>
          <p class="kpi-desc">{{ vm()?.countryLabel }} &middot; {{ vm()?.reviewLabel }}</p>
          @if (vm()?.profileBadge) { <p class="kpi-badge-text">{{ vm()?.profileBadge }}</p> }
          <a [routerLink]="['/management/properties', vm()?.propId, 'edit']" class="kpi-action">
            <span class="material-symbols-outlined">edit</span> Editar Contenido
          </a>
        </div>
      </article>

      <article class="kpi-card">
        <div class="kpi-icon-wrap" style="--card-accent: var(--success)">
          <span class="material-symbols-outlined kpi-icon">payments</span>
        </div>
        <div class="kpi-body">
          <p class="kpi-label">Precio Promedio</p>
          <h3 class="kpi-value">\${{ vm()?.avgPriceLabel }}</h3>
          <p class="kpi-desc">Fuente: {{ vm()?.sourceCollection }}</p>
        </div>
      </article>

      <article class="kpi-card">
        <div class="kpi-icon-wrap" style="--card-accent: var(--warning)">
          <span class="material-symbols-outlined kpi-icon">meeting_room</span>
        </div>
        <div class="kpi-body">
          <p class="kpi-label">Tipos Configurados</p>
          <h3 class="kpi-value">{{ vm()?.totalRoomTypes }}</h3>
          <p class="kpi-desc">Capacidad operativa del hotel</p>
        </div>
      </article>

      <article class="kpi-card">
        <div class="kpi-icon-wrap" style="--card-accent: var(--accent)">
          <span class="material-symbols-outlined kpi-icon">door_front</span>
        </div>
        <div class="kpi-body">
          <p class="kpi-label">Habitaciones Físicas</p>
          <h3 class="kpi-value">{{ vm()?.totalHotelRooms }}</h3>
          <p class="kpi-desc">Registros en hotel_rooms</p>
        </div>
      </article>
    </section>
  `
})
export class RpKpiGridComponent {
  readonly vm = input<any>(null);
}
