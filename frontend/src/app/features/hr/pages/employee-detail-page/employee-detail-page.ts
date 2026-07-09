import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { switchMap } from 'rxjs';

import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { HrApiService } from '../../services/hr-api.service';

@Component({
  selector: 'app-employee-detail-page',
  standalone: true,
  imports: [PageHeaderComponent, LoadingStateComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div style="max-width: 800px; margin: 0 auto; padding: 24px;">
      <app-page-header eyebrow="RRHH" title="Perfil de Empleado" description="Información detallada del empleado." />

      <button (click)="goBack()" style="display: inline-flex; align-items: center; gap: 6px; background: none; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 16px; font-size: 13px; cursor: pointer; margin-bottom: 16px; color: #475569;">
        <span class="material-symbols-outlined" style="font-size: 16px;">arrow_back</span> Volver
      </button>

      @switch (viewState()) {
        @case ('loading') { <app-loading-state label="Cargando empleado..." /> }
        @case ('error') { <div style="padding: 24px; text-align: center; color: #dc2626;">Error al cargar el empleado.</div> }
        @default {
          @if (emp(); as e) {
            <!-- Profile Header -->
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; margin-bottom: 20px;">
              <div style="display: flex; align-items: center; gap: 16px;">
                <div style="width: 56px; height: 56px; border-radius: 50%; background: linear-gradient(135deg, #2563eb, #7c3aed); display: flex; align-items: center; justify-content: center; color: white; font-size: 24px; font-weight: 700;">
                  {{ e.fullName.charAt(0).toUpperCase() }}
                </div>
                <div style="flex: 1;">
                  <h2 style="margin: 0; font-size: 20px; font-weight: 600; color: #0f172a;">{{ e.fullName }}</h2>
                  <p style="margin: 2px 0 0; font-size: 13px; color: #64748b;">{{ e.position }} · {{ e.department }}</p>
                </div>
                <span [style]="e.isActive ? 'background:#f0fdf4;color:#166534;' : 'background:#fef2f2;color:#991b1b;'"
                  style="padding: 4px 10px; border-radius: 999px; font-size: 11px; font-weight: 600;">
                  {{ e.isActive ? 'Activo' : 'Inactivo' }}
                </span>
              </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
              <!-- Personal Info -->
              <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px;">
                <h4 style="font-size: 13px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.03em; margin: 0 0 16px;">Información Personal</h4>
                <div style="display: flex; flex-direction: column; gap: 10px; font-size: 13px;">
                  <div><span style="color: #64748b;">Documento:</span> <span style="color: #0f172a; font-weight: 500;">{{ e.idDocument }}</span></div>
                  <div><span style="color: #64748b;">Email:</span> <span style="color: #0f172a;">{{ e.email || '—' }}</span></div>
                  <div><span style="color: #64748b;">Teléfono:</span> <span style="color: #0f172a;">{{ e.phone || '—' }}</span></div>
                  <div><span style="color: #64748b;">Dirección:</span> <span style="color: #0f172a;">{{ e.address || '—' }}</span></div>
                </div>
              </div>

              <!-- Employment Info -->
              <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px;">
                <h4 style="font-size: 13px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.03em; margin: 0 0 16px;">Información Laboral</h4>
                <div style="display: flex; flex-direction: column; gap: 10px; font-size: 13px;">
                  <div><span style="color: #64748b;">Departamento:</span> <span style="color: #0f172a; font-weight: 500;">{{ e.department || '—' }}</span></div>
                  <div><span style="color: #64748b;">Puesto:</span> <span style="color: #0f172a; font-weight: 500;">{{ e.position || '—' }}</span></div>
                  <div><span style="color: #64748b;">Contratación:</span> <span style="color: #0f172a;">{{ e.hireDate || '—' }}</span></div>
                  <div><span style="color: #64748b;">Salario:</span> <span style="color: #0f172a;">{{ e.salary ? '$' + e.salary.toLocaleString() : '—' }}</span></div>
                </div>
              </div>

              <!-- Emergency -->
              <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px;">
                <h4 style="font-size: 13px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.03em; margin: 0 0 16px;">Contacto de Emergencia</h4>
                <div style="display: flex; flex-direction: column; gap: 10px; font-size: 13px;">
                  <div><span style="color: #64748b;">Contacto:</span> <span style="color: #0f172a;">{{ e.emergencyContact || '—' }}</span></div>
                  <div><span style="color: #64748b;">Teléfono:</span> <span style="color: #0f172a;">{{ e.emergencyPhone || '—' }}</span></div>
                </div>
              </div>

              <!-- Credenciales -->
              <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px;">
                <h4 style="font-size: 13px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.03em; margin: 0 0 16px;">
                  <span class="material-symbols-outlined" style="font-size: 16px; vertical-align: middle; margin-right: 4px;">key</span>
                  Credenciales de Acceso
                </h4>
                @if (e.username) {
                  <div style="display: flex; flex-direction: column; gap: 10px; font-size: 13px;">
                    <div>
                      <span style="color: #64748b;">Usuario:</span>
                      <span style="color: #0f172a; font-weight: 600; font-family: monospace; margin-left: 4px;">{{ e.username }}</span>
                    </div>
                    @if (e.password) {
                      <div>
                        <span style="color: #64748b;">Contraseña:</span>
                        <span style="color: #0f172a; font-weight: 600; font-family: monospace; margin-left: 4px; background: #fffbeb; padding: 2px 6px; border-radius: 4px; border: 1px solid #fde68a;">{{ e.password }}</span>
                        <span style="color: #dc2626; font-size: 11px; margin-left: 6px;">(copia esta clave, solo se muestra una vez)</span>
                      </div>
                    } @else {
                      <div style="color: #64748b; font-size: 12px;">
                        <span class="material-symbols-outlined" style="font-size: 14px; vertical-align: middle;">check_circle</span>
                        Usuario ya vinculado. La contraseña se configuró al crear la cuenta.
                      </div>
                    }
                  </div>
                } @else {
                  <div style="color: #64748b; font-size: 12px;">Generando credenciales...</div>
                }
              </div>

              <!-- Notes -->
              @if (e.notes) {
                <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px;">
                  <h4 style="font-size: 13px; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.03em; margin: 0 0 8px;">Notas</h4>
                  <p style="font-size: 13px; color: #334155; margin: 0;">{{ e.notes }}</p>
                </div>
              }
            </div>
          }
        }
      }
    </div>
  `
})
export class EmployeeDetailPageComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly hrApi = inject(HrApiService);

  readonly viewState = signal<'loading' | 'success' | 'error'>('loading');
  readonly emp = signal<any>(null);

  constructor() {
    this.route.paramMap.pipe(
      switchMap(params => {
        this.viewState.set('loading');
        return this.hrApi.getEmployee(params.get('employeeId')!);
      }),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (data) => { this.emp.set(data); this.viewState.set('success'); },
      error: () => this.viewState.set('error'),
    });
  }

  goBack() { this.router.navigate(['/management/hr/directory']); }
}
