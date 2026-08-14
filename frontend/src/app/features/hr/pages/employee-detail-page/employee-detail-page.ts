import { httpResource } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';

import { getErrorStatus } from '../../../../shared/utils/http-error.util';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import type { EmployeeDetailDto } from '../../models/hr.dto';
import { mapEmployeeDetail } from '../../mappers/hr.mapper';

@Component({
  selector: 'app-employee-detail-page',
  standalone: true,
  imports: [PageHeaderComponent, LoadingStateComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="employee-detail-page">
      <app-page-header
        eyebrow="RRHH"
        title="Perfil de empleado"
        description="Información detallada y credenciales de acceso."
      />

      <button type="button" class="back-button" (click)="goBack()">
        <span class="material-symbols-outlined" aria-hidden="true">arrow_back</span>
        Volver al directorio
      </button>

      @switch (viewState()) {
        @case ('loading') {
          <section class="state-card">
            <app-loading-state label="Cargando empleado..." />
          </section>
        }
        @case ('error') {
          <section class="state-card state-card--error" role="alert">
            <span class="material-symbols-outlined" aria-hidden="true">error</span>
            <h2>No se pudo cargar el empleado</h2>
            <p>Verifica que el registro exista y que tengas permiso para consultarlo.</p>
            <button type="button" class="secondary-button" (click)="goBack()">Volver al directorio</button>
          </section>
        }
        @case ('empty') {
          <section class="state-card">
            <span class="material-symbols-outlined" aria-hidden="true">person_search</span>
            <h2>Empleado no encontrado</h2>
            <p>El registro solicitado no existe o ya no está disponible.</p>
            <button type="button" class="secondary-button" (click)="goBack()">Volver al directorio</button>
          </section>
        }
        @default {
          @if (emp(); as e) {
            <section class="profile-card">
              <div class="profile-identity">
                <div class="avatar" aria-hidden="true">{{ initials() }}</div>
                <div class="profile-copy">
                  <span class="profile-kicker">Ficha de colaborador</span>
                  <h2>{{ e.fullName }}</h2>
                  <p>{{ e.position || 'Puesto no especificado' }}<span class="dot-separator">·</span>{{ e.department || 'Sin departamento' }}</p>
                </div>
              </div>
              <span class="status-badge" [class.status-badge--active]="e.isActive" [class.status-badge--inactive]="!e.isActive">
                <span class="status-dot" aria-hidden="true"></span>
                {{ e.isActive ? 'Activo' : 'Inactivo' }}
              </span>
            </section>

            <div class="info-grid">
              <section class="info-card">
                <div class="card-heading">
                  <span class="icon-box icon-box--blue"><span class="material-symbols-outlined" aria-hidden="true">person</span></span>
                  <div>
                    <h3>Información personal</h3>
                    <p>Datos de contacto del empleado</p>
                  </div>
                </div>
                <dl class="info-list">
                  <div><dt>Documento</dt><dd>{{ e.idDocument || '—' }}</dd></div>
                  <div><dt>Email</dt><dd>{{ e.email || '—' }}</dd></div>
                  <div><dt>Teléfono</dt><dd>{{ e.phone || '—' }}</dd></div>
                  <div><dt>Dirección</dt><dd>{{ e.address || '—' }}</dd></div>
                </dl>
              </section>

              <section class="info-card">
                <div class="card-heading">
                  <span class="icon-box icon-box--purple"><span class="material-symbols-outlined" aria-hidden="true">work</span></span>
                  <div>
                    <h3>Información laboral</h3>
                    <p>Asignación y condiciones del puesto</p>
                  </div>
                </div>
                <dl class="info-list">
                  <div><dt>Departamento</dt><dd>{{ e.department || '—' }}</dd></div>
                  <div><dt>Puesto</dt><dd>{{ e.position || '—' }}</dd></div>
                  <div><dt>Contratación</dt><dd>{{ e.hireDate || '—' }}</dd></div>
                  <div><dt>Salario</dt><dd>{{ e.salary !== null && e.salary !== undefined ? ('$' + e.salary.toLocaleString()) : '—' }}</dd></div>
                </dl>
              </section>

              <section class="info-card">
                <div class="card-heading">
                  <span class="icon-box icon-box--amber"><span class="material-symbols-outlined" aria-hidden="true">emergency</span></span>
                  <div>
                    <h3>Contacto de emergencia</h3>
                    <p>Persona de contacto registrada</p>
                  </div>
                </div>
                <dl class="info-list">
                  <div><dt>Contacto</dt><dd>{{ e.emergencyContact || '—' }}</dd></div>
                  <div><dt>Teléfono</dt><dd>{{ e.emergencyPhone || '—' }}</dd></div>
                </dl>
              </section>

              <section class="info-card credentials-card">
                <div class="card-heading">
                  <span class="icon-box icon-box--green"><span class="material-symbols-outlined" aria-hidden="true">key</span></span>
                  <div>
                    <h3>Credenciales de acceso</h3>
                    <p>Información sensible de la cuenta</p>
                  </div>
                </div>
                @if (e.username) {
                  <dl class="info-list">
                    <div><dt>Usuario</dt><dd class="monospace-value">{{ e.username }}</dd></div>
                    @if (e.password) {
                      <div class="password-row">
                        <dt>Contraseña temporal</dt>
                        <dd>
                          <span class="secret-value">{{ e.password }}</span>
                          <small>Guárdala ahora; solo se muestra durante esta consulta.</small>
                        </dd>
                      </div>
                    } @else {
                      <div><dt>Estado</dt><dd class="credential-confirmed"><span class="material-symbols-outlined" aria-hidden="true">verified_user</span> Cuenta ya configurada</dd></div>
                    }
                  </dl>
                } @else {
                  <p class="muted-message">Las credenciales se están generando...</p>
                }
              </section>

              @if (e.notes) {
                <section class="info-card notes-card">
                  <div class="card-heading">
                    <span class="icon-box icon-box--blue"><span class="material-symbols-outlined" aria-hidden="true">notes</span></span>
                    <div><h3>Notas</h3><p>Observaciones internas</p></div>
                  </div>
                  <p class="notes-copy">{{ e.notes }}</p>
                </section>
              }
            </div>
          }
        }
      }
    </main>
  `,
  styles: [`
    :host { display: block; min-height: 100%; }

    .employee-detail-page {
      max-width: 1040px;
      margin: 0 auto;
      padding: 24px;
      color: var(--app-text);
    }

    .back-button, .secondary-button {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border: 1px solid var(--app-border);
      border-radius: 10px;
      background: var(--surface);
      color: var(--app-text);
      cursor: pointer;
      font: inherit;
      transition: background .18s ease, border-color .18s ease, transform .18s ease;
    }

    .back-button {
      padding: 9px 14px;
      margin: 4px 0 20px;
      font-size: 13px;
      color: var(--muted-text);
    }

    .back-button .material-symbols-outlined { font-size: 18px; color: var(--accent); }
    .back-button:hover, .secondary-button:hover { background: var(--surface-hover); border-color: var(--accent); transform: translateY(-1px); }

    .profile-card, .info-card, .state-card {
      background: var(--surface);
      border: 1px solid var(--app-border);
      border-radius: 16px;
      box-shadow: var(--shadow-sm);
    }

    .profile-card {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      padding: 24px;
      margin-bottom: 20px;
      background: linear-gradient(135deg, var(--surface-raised), var(--surface));
    }

    .profile-identity { display: flex; align-items: center; gap: 16px; min-width: 0; }
    .avatar {
      display: grid;
      place-items: center;
      flex: 0 0 64px;
      width: 64px;
      height: 64px;
      border-radius: 18px;
      background: linear-gradient(135deg, var(--accent), var(--purple));
      color: var(--on-accent);
      font-size: 25px;
      font-weight: 750;
      letter-spacing: .02em;
      box-shadow: 0 10px 24px color-mix(in srgb, var(--accent) 22%, transparent);
    }

    .profile-copy { min-width: 0; }
    .profile-kicker { color: var(--accent); font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
    .profile-copy h2 { margin: 4px 0 5px; color: var(--app-text); font-size: 22px; line-height: 1.2; overflow-wrap: anywhere; }
    .profile-copy p { margin: 0; color: var(--muted-text); font-size: 13px; }
    .dot-separator { margin: 0 7px; color: var(--app-border); }

    .status-badge { display: inline-flex; align-items: center; gap: 7px; flex: 0 0 auto; padding: 6px 11px; border-radius: 999px; font-size: 11px; font-weight: 700; }
    .status-badge--active { background: var(--success-light); color: var(--success-strong); }
    .status-badge--inactive { background: var(--danger-light); color: var(--danger-strong); }
    .status-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }

    .info-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
    .info-card { padding: 20px; min-width: 0; }
    .notes-card { grid-column: 1 / -1; }
    .card-heading { display: flex; align-items: center; gap: 11px; padding-bottom: 15px; border-bottom: 1px solid var(--app-border); }
    .card-heading h3 { margin: 0; color: var(--app-text); font-size: 14px; font-weight: 700; }
    .card-heading p { margin: 3px 0 0; color: var(--muted-text); font-size: 11px; }
    .icon-box { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 10px; }
    .icon-box .material-symbols-outlined { font-size: 19px; }
    .icon-box--blue { background: var(--accent-light); color: var(--accent-strong); }
    .icon-box--purple { background: var(--purple-light); color: var(--purple-strong); }
    .icon-box--amber { background: var(--warning-light); color: var(--warning-strong); }
    .icon-box--green { background: var(--success-light); color: var(--success-strong); }

    .info-list { display: flex; flex-direction: column; gap: 13px; margin: 17px 0 0; }
    .info-list > div { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; }
    .info-list dt { color: var(--muted-text); font-size: 12px; flex: 0 0 auto; }
    .info-list dd { margin: 0; color: var(--app-text); font-size: 13px; font-weight: 600; text-align: right; overflow-wrap: anywhere; }
    .monospace-value, .secret-value { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    .password-row { align-items: flex-start !important; }
    .password-row dd { display: flex; flex-direction: column; align-items: flex-end; gap: 5px; }
    .secret-value { padding: 5px 8px; border: 1px solid var(--warning); border-radius: 7px; background: var(--warning-light); color: var(--warning-strong); }
    .password-row small { max-width: 210px; color: var(--muted-text); font-size: 10px; font-weight: 400; line-height: 1.35; }
    .credential-confirmed { display: inline-flex; align-items: center; gap: 5px; color: var(--success) !important; }
    .credential-confirmed .material-symbols-outlined { font-size: 16px; }
    .muted-message, .notes-copy { color: var(--muted-text); font-size: 13px; line-height: 1.55; }
    .muted-message { margin: 17px 0 0; }
    .notes-copy { margin: 16px 0 0; white-space: pre-wrap; }

    .state-card { display: grid; place-items: center; gap: 8px; min-height: 220px; padding: 28px; text-align: center; }
    .state-card > .material-symbols-outlined { color: var(--accent); font-size: 38px; }
    .state-card--error > .material-symbols-outlined { color: var(--danger); }
    .state-card h2 { margin: 2px 0 0; color: var(--app-text); font-size: 17px; }
    .state-card p { max-width: 420px; margin: 0; color: var(--muted-text); font-size: 13px; }
    .secondary-button { padding: 9px 14px; margin-top: 8px; font-size: 12px; font-weight: 600; }

    @media (max-width: 700px) {
      .employee-detail-page { padding: 16px; }
      .profile-card { align-items: flex-start; flex-direction: column; padding: 18px; }
      .status-badge { margin-left: 80px; }
      .info-grid { grid-template-columns: 1fr; gap: 14px; }
      .notes-card { grid-column: auto; }
    }
  `],
})
export class EmployeeDetailPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  private readonly paramMap = toSignal(this.route.paramMap, {
    initialValue: this.route.snapshot.paramMap,
  });
  readonly empId = computed(() => this.paramMap().get('employeeId') ?? '');

  readonly detailResource = httpResource<EmployeeDetailDto>(() => {
    const id = this.empId();
    return id ? `/api/hr/${id}` : undefined;
  });

  readonly emp = computed(() => {
    // value() LANZA cuando el request falló — leer error() antes para degradar.
    if (this.detailResource.error()) return null;
    const dto = this.detailResource.value();
    if (!dto) return null;
    const mapped = mapEmployeeDetail(dto);
    return {
      ...mapped,
      fullName: mapped.fullName?.trim() || 'Empleado sin nombre',
      position: mapped.position?.trim() || '',
      department: mapped.department?.trim() || '',
    };
  });

  readonly initials = computed(() => {
    const name = this.emp()?.fullName?.trim() || 'E';
    return name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map(part => part.charAt(0).toUpperCase())
      .join('') || 'E';
  });

  readonly viewState = computed<'loading' | 'success' | 'error' | 'empty'>(() => {
    // error() ANTES de value(): value() lanza cuando el request falló.
    const error = this.detailResource.error();
    if (error) return getErrorStatus(error) === 404 ? 'empty' : 'error';
    const value = this.detailResource.value();
    if (this.detailResource.isLoading() && !value) return 'loading';
    return value ? 'success' : 'loading';
  });

  goBack(): void { this.router.navigate(['/management/hr/directory']); }
}
