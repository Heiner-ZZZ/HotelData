import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { HrApiService } from '../../services/hr-api.service';
import { API_CONFIG } from '../../../../core/api/api.config';
import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';

@Component({
  selector: 'app-employee-onboarding-page',
  standalone: true,
  imports: [FormsModule, PropertySelectorComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="onboarding-page" style="max-width: 1100px; margin: 0 auto; padding: 24px;">
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 24px;">
        <div>
          <h1 style="font-size: 22px; font-weight: 700; color: #0f172a; margin: 0 0 4px;">Alta de Nuevo Empleado</h1>
          <p style="font-size: 13px; color: #64748b; margin: 0;">Registro y configuración inicial para nuevas contrataciones.</p>
        </div>
        <div style="display: flex; gap: 8px;">
          <button (click)="submit()" class="btn-primary" [disabled]="submitting() || step() < 4"
            style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; opacity: 0.4;">
            @if (submitting()) { Guardando... } @else { Finalizar Registro }
          </button>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 320px; gap: 24px;">
        <div style="min-width: 0;">

      <!-- Stepper -->
      <div style="display: flex; align-items: center; justify-content: space-between; background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px 24px; margin-bottom: 24px; position: relative;">
        <div style="position: absolute; left: 60px; right: 60px; top: 50%; height: 2px; background: #e2e8f0; z-index: 0;"></div>
        @for (s of steps; track s.num; let i = $index) {
          <div style="display: flex; flex-direction: column; align-items: center; gap: 6px; background: white; padding: 0 8px; z-index: 1; cursor: pointer;" (click)="step() >= s.num && step.set(s.num)">
            <div [style]="step() >= s.num ? 'background:#2563eb;color:white;' : 'background:#f1f5f9;color:#94a3b8;'"
              style="width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 600; transition: all 0.2s;">
              {{ s.num }}
            </div>
            <span [style]="step() >= s.num ? 'color:#0f172a;font-weight:600;' : 'color:#94a3b8;'"
              style="font-size: 11px; white-space: nowrap;">{{ s.label }}</span>
          </div>
        }
      </div>

      @if (error()) {
        <div style="padding: 10px 14px; background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; border-radius: 8px; font-size: 12px; margin-bottom: 16px;">{{ error() }}</div>
      }
      @if (success()) {
        <div style="padding: 10px 14px; background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; border-radius: 8px; font-size: 12px; margin-bottom: 16px;">{{ success() }}</div>
      }

      <!-- Step 1: Personal Info -->
      @if (step() === 1) {
        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px;">
          <h3 style="font-size: 16px; font-weight: 600; color: #0f172a; margin: 0 0 4px;">Información Personal</h3>
          <p style="font-size: 12px; color: #94a3b8; margin: 0 0 20px;">Datos básicos del nuevo empleado.</p>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <div style="grid-column: 1 / -1;">
              <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">Nombre Completo <span style="color: #dc2626;">*</span></label>
              <input type="text" [(ngModel)]="form.fullName"
                style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
            </div>
            <div>
              <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">ID / Pasaporte <span style="color: #dc2626;">*</span></label>
              <input type="text" [(ngModel)]="form.idDocument"
                style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
            </div>
            <div>
              <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">Teléfono</label>
              <input type="tel" [(ngModel)]="form.phone"
                style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
            </div>
            <div>
              <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">Email Corporativo</label>
              <input type="email" [(ngModel)]="form.email"
                style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
            </div>
            <div style="grid-column: 1 / -1;">
              <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">Dirección</label>
              <input type="text" [(ngModel)]="form.address"
                style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
            </div>
          </div>
          <div style="margin-top: 20px; display: flex; justify-content: flex-end;">
            <button (click)="nextStep()" [disabled]="!form.fullName || !form.idDocument"
              style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; &:disabled { opacity: 0.4; }">
              Siguiente →
            </button>
          </div>
        </div>
      }

      <!-- Step 2: Employment Details + Replacement -->
      @if (step() === 2) {
        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px;">
          <h3 style="font-size: 16px; font-weight: 600; color: #0f172a; margin: 0 0 4px;">Detalles de Empleo</h3>
          <p style="font-size: 12px; color: #94a3b8; margin: 0 0 20px;">Puesto, departamento y configuración laboral.</p>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
            <div>
              <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">Departamento</label>
              <input type="text" [(ngModel)]="form.department" placeholder="Ej: Recepción"
                style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
            </div>
            <div>
              <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">Puesto</label>
              <input type="text" [(ngModel)]="form.position" placeholder="Ej: Recepcionista"
                style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
            </div>
            <div>
              <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">Fecha de Contratación</label>
              <input type="date" [(ngModel)]="form.hireDate"
                style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
            </div>
            <div>
              <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">Salario (MXN)</label>
              <input type="number" [(ngModel)]="form.salary"
                style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
            </div>
            <div>
              <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">Contacto de Emergencia</label>
              <input type="text" [(ngModel)]="form.emergencyContact"
                style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
            </div>
            <div>
              <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">Tel. Emergencia</label>
              <input type="tel" [(ngModel)]="form.emergencyPhone"
                style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
            </div>
            <div style="grid-column: 1 / -1;">
              <label style="font-size: 12px; font-weight: 500; color: #475569; display: block; margin-bottom: 4px;">Notas</label>
              <textarea [(ngModel)]="form.notes" rows="2" placeholder="Observaciones adicionales..."
                style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; font-family: inherit; box-sizing: border-box; resize: vertical; outline: none;"></textarea>
            </div>
          </div>

          <!-- User Account Link -->
          <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #f1f5f9;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
              <h4 style="font-size: 14px; font-weight: 600; color: #0f172a; margin: 0;">Cuenta de Usuario</h4>
              @if (!selectedUser()) {
                <button type="button" (click)="openCreateUserModal()"
                  style="display: flex; align-items: center; gap: 4px; padding: 5px 12px; background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; border-radius: 6px; font-size: 11px; font-weight: 500; cursor: pointer;">
                  <span class="material-symbols-outlined" style="font-size: 14px;">person_add</span>
                  Crear usuario
                </button>
              }
            </div>
            <p style="font-size: 11px; color: #94a3b8; margin: 0 0 10px;">Vincula este empleado a una cuenta de usuario existente para que pueda iniciar sesión.</p>

            @if (selectedUser(); as user) {
              <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span class="material-symbols-outlined" style="color: #16a34a; font-size: 20px;">person_check</span>
                  <div>
                    <span style="font-size: 13px; font-weight: 500; color: #166534;">{{ user.display_name || user.username }}</span>
                    <span style="font-size: 11px; color: #15803d; display: block;">{{ user.email }}</span>
                    <span style="font-size: 10px; color: #65a30d;">{{ user.primary_role }}</span>
                  </div>
                </div>
                <button type="button" (click)="clearUser()"
                  style="background: none; border: none; color: #16a34a; cursor: pointer; font-size: 18px; padding: 2px;" title="Desvincular">
                  <span class="material-symbols-outlined">close</span>
                </button>
              </div>
            } @else {
              <div style="position: relative;">
                <div style="display: flex; align-items: center; gap: 0; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
                  <span class="material-symbols-outlined" style="color: #94a3b8; font-size: 18px; padding: 0 0 0 10px;">search</span>
                  <input type="text"
                    [value]="userSearchFilter()"
                    (input)="userSearchFilter.set($any($event).target.value); userDropdownOpen.set(true)"
                    (focus)="searchUsers(); userDropdownOpen.set(true)"
                    (blur)="closeUserDropdown()"
                    placeholder="Buscar usuario por nombre o email..."
                    style="flex: 1; padding: 8px 10px; border: none; font-size: 13px; outline: none;" />
                  @if (usersLoading()) {
                    <span class="material-symbols-outlined spinning" style="color: #94a3b8; font-size: 16px; padding: 0 10px;">sync</span>
                  }
                </div>
                @if (userDropdownOpen()) {
                  <ul style="position: absolute; top: 100%; left: 0; right: 0; z-index: 10; background: white; border: 1px solid #e2e8f0; border-radius: 8px; margin: 4px 0 0; padding: 4px 0; list-style: none; max-height: 200px; overflow-y: auto; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                    @for (u of filteredUsers(); track u.user_id) {
                      <li (mousedown)="selectUser(u)"
                        style="padding: 8px 14px; cursor: pointer; font-size: 13px; display: flex; flex-direction: column; gap: 1px; transition: background 0.15s;"
                        (mouseenter)="userHovered.set(u.user_id)" (mouseleave)="userHovered.set(null)"
                        [style.background]="userHovered() === u.user_id ? '#f1f5f9' : ''">
                        <span style="font-weight: 500; color: #0f172a;">{{ u.display_name || u.username }}</span>
                        <span style="font-size: 11px; color: #64748b;">{{ u.email }} · {{ u.primary_role }}</span>
                      </li>
                    } @empty {
                      <li style="padding: 10px 14px; font-size: 12px; color: #94a3b8; text-align: center;">
                        @if (usersLoading()) {
                          Buscando usuarios...
                        } @else {
                          No se encontraron usuarios{{ userSearchFilter() ? ' para "' + userSearchFilter() + '"' : '' }}
                        }
                      </li>
                    }
                  </ul>
                }
              </div>
            }
            <p style="font-size: 10px; color: #94a3b8; margin: 4px 0 0;">Selecciona un usuario para vincularlo al empleado, o crea uno nuevo con el botón superior.</p>
          </div>

          <!-- Replacement Logic -->
          <div style="margin-top: 24px; padding-top: 20px; border-top: 1px solid #f1f5f9;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
              <div>
                <h4 style="font-size: 14px; font-weight: 600; color: #0f172a; margin: 0;">Lógica de Reemplazo</h4>
                <p style="font-size: 11px; color: #94a3b8; margin: 2px 0 0;">¿Este empleado reemplaza a alguien?</p>
              </div>
              <label style="position: relative; display: inline-flex; align-items: center; cursor: pointer;">
                <input type="checkbox" [(ngModel)]="form.replacesEmployee" class="sr-only"
                  style="position: absolute; opacity: 0; width: 0; height: 0;" />
                <div [style]="form.replacesEmployee ? 'background:#2563eb;' : 'background:#e2e8f0;'"
                  style="width: 40px; height: 22px; border-radius: 999px; transition: all 0.2s; position: relative;">
                  <div [style]="form.replacesEmployee ? 'transform: translateX(18px);' : 'transform: translateX(2px);'"
                    style="width: 18px; height: 18px; background: white; border-radius: 50%; position: absolute; top: 2px; transition: all 0.2s;"></div>
                </div>
              </label>
            </div>
            @if (form.replacesEmployee) {
              <div style="background: #f0f4ff; border: 1px solid #e0e7ff; border-radius: 10px; padding: 16px;">
                <p style="font-size: 12px; color: #4338ca; margin: 0 0 10px;">Selecciona al empleado a reemplazar y qué transferir:</p>
                <input type="text" [(ngModel)]="form.replacesEmployeeId" placeholder="ID del empleado a reemplazar..."
                  style="width: 100%; padding: 8px 12px; border: 1px solid #e0e7ff; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none; margin-bottom: 10px;" />
                <div style="display: flex; gap: 16px; flex-wrap: wrap;">
                  <label style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: #334155; cursor: pointer;">
                    <input type="checkbox" [(ngModel)]="form.transferShifts" /> Transferir turnos
                  </label>
                  <label style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: #334155; cursor: pointer;">
                    <input type="checkbox" [(ngModel)]="form.transferPermissions" /> Transferir permisos
                  </label>
                  <label style="display: flex; align-items: center; gap: 6px; font-size: 12px; color: #334155; cursor: pointer;">
                    <input type="checkbox" [(ngModel)]="form.transferTasks" /> Transferir tareas
                  </label>
                </div>
              </div>
            }
          </div>

          <div style="margin-top: 20px; display: flex; justify-content: space-between;">
            <button (click)="prevStep()"
              style="padding: 10px 20px; background: white; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; cursor: pointer;">
              ← Anterior
            </button>
            <button (click)="nextStep()"
              style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer;">
              Siguiente →
            </button>
          </div>
        </div>
      }

      <!-- Step 3: Confirmation -->
      @if (step() === 3) {
        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px;">
          <h3 style="font-size: 16px; font-weight: 600; color: #0f172a; margin: 0 0 4px;">Confirmación</h3>
          <p style="font-size: 12px; color: #94a3b8; margin: 0 0 20px;">Revisa los datos antes de finalizar.</p>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 13px;">
            <div><strong>Nombre:</strong> {{ form.fullName }}</div>
            <div><strong>Documento:</strong> {{ form.idDocument }}</div>
            <div><strong>Email:</strong> {{ form.email || '—' }}</div>
            <div><strong>Teléfono:</strong> {{ form.phone || '—' }}</div>
            <div><strong>Departamento:</strong> {{ form.department || '—' }}</div>
            <div><strong>Puesto:</strong> {{ form.position || '—' }}</div>
            <div><strong>Contratación:</strong> {{ form.hireDate || '—' }}</div>
            <div><strong>Salario:</strong> {{ form.salary ? '$' + form.salary.toLocaleString() : '—' }}</div>
            <div><strong>Usuario vinculado:</strong> {{ selectedUserLabel() || '—' }}</div>
          </div>
          @if (form.replacesEmployee && form.replacesEmployeeId) {
            <div style="margin-top: 16px; padding: 10px; background: #f0f4ff; border-radius: 8px; font-size: 12px; color: #4338ca;">
              Reemplazará al empleado ID: {{ form.replacesEmployeeId }}
              @if (form.transferShifts) { · Turnos }
              @if (form.transferPermissions) { · Permisos }
              @if (form.transferTasks) { · Tareas }
            </div>
          }
          <div style="margin-top: 20px; display: flex; justify-content: space-between;">
            <button (click)="prevStep()" style="padding: 10px 20px; background: white; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; cursor: pointer;">← Anterior</button>
            <button (click)="step.set(4)" style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer;">Finalizar →</button>
          </div>
        </div>
      }

      <!-- Step 4: Submit -->
      @if (step() === 4) {
        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; text-align: center;">
          <span class="material-symbols-outlined" style="font-size: 48px; color: #22c55e;">check_circle</span>
          <h3 style="font-size: 18px; font-weight: 600; color: #0f172a; margin: 12px 0 4px;">¿Listo para registrar?</h3>
          <p style="font-size: 13px; color: #64748b; margin: 0 0 20px;">Al confirmar se creará el empleado en el sistema.</p>
          <button (click)="submit()" [disabled]="submitting()"
            style="padding: 12px 32px; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer;">
            {{ submitting() ? 'Registrando...' : 'Confirmar y Registrar' }}
          </button>
        </div>
      }
        </div>

        <!-- Right Sidebar: Document Checklist -->
        <div style="min-width: 0;">
          <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
              <span class="material-symbols-outlined" style="color: #2563eb; font-size: 18px;">assignment</span>
              <h3 style="font-size: 14px; font-weight: 600; color: #0f172a; margin: 0;">Documentación Obligatoria</h3>
            </div>
            <p style="font-size: 11px; color: #94a3b8; margin: 0 0 16px;">Archivos requeridos para completar el alta.</p>

            <ul style="list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 10px;">
              @for (doc of documentChecklist(); track doc.key) {
                <li style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; display: flex; flex-direction: column; gap: 8px;">
                  <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; gap: 6px;">
                      <span class="material-symbols-outlined" style="font-size: 16px; color: #cbd5e1;">{{ doc.icon }}</span>
                      <span style="font-size: 12px; font-weight: 500; color: #1e293b;">{{ doc.label }}</span>
                    </div>
                    <span [style]="doc.status === 'completed' ? 'background:#dcfce7;color:#166534;' : 'background:#fee2e2;color:#991b1b;'"
                      style="padding: 2px 8px; border-radius: 999px; font-size: 10px; font-weight: 600;">
                      {{ doc.status === 'completed' ? 'Completado' : 'Pendiente' }}
                    </span>
                  </div>
                  @if (doc.status === 'completed') {
                    <div style="display: flex; align-items: center; gap: 6px; font-size: 11px; color: #64748b; background: white; padding: 6px 8px; border-radius: 6px; border: 1px solid #f1f5f9;">
                      <span class="material-symbols-outlined" style="font-size: 14px;">picture_as_pdf</span>
                      <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ doc.filename }}</span>
                    </div>
                  } @else {
                    <button (click)="uploadDocument(doc.key)"
                      style="width: 100%; padding: 6px 0; background: transparent; border: 1px dashed #cbd5e1; border-radius: 6px; font-size: 11px; color: #64748b; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 4px;">
                      <span class="material-symbols-outlined" style="font-size: 14px;">upload</span>
                      Subir Archivo
                    </button>
                  }
                </li>
              }
            </ul>

            <!-- Hotel Assignment -->
            <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #f1f5f9;">
              <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 8px;">
                <span class="material-symbols-outlined" style="font-size: 16px; color: #2563eb;">hotel</span>
                <span style="font-size: 12px; font-weight: 600; color: #0f172a;">Asignación a Hotel</span>
              </div>
              @if (hasCurrentHotel) {
                <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 10px 12px; font-size: 12px; color: #166534;">
                  <span class="material-symbols-outlined" style="font-size: 14px; vertical-align: middle; margin-right: 4px;">check_circle</span>
                  Asignado automáticamente a <strong>{{ propCtx.currentPropLabel() }}</strong>
                </div>
                <p style="font-size: 10px; color: #94a3b8; margin: 4px 0 0;">El nuevo empleado trabajará en el mismo hotel que tú.</p>
              } @else {
                <app-property-selector
                  [selectedPropId]="form.propId ?? 0"
                  (propIdChange)="onHotelSelected($event)">
                </app-property-selector>
                <p style="font-size: 10px; color: #94a3b8; margin: 4px 0 0;">Selecciona el hotel al que se asignará el empleado.</p>
              }
            </div>
          </div>
        </div>
      </div>

      <!-- Create User Quick Modal -->
      @if (showCreateUserModal()) {
        <div style="position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center;" (click)="closeCreateUserModal()">
          <div style="position: absolute; inset: 0; background: rgba(0,0,0,0.4);"></div>
          <div (click)="$event.stopPropagation()" style="position: relative; background: white; border-radius: 14px; padding: 28px; width: 440px; max-width: 95vw; box-shadow: 0 20px 60px rgba(0,0,0,0.15); max-height: 90vh; overflow-y: auto;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
              <div style="display: flex; align-items: center; gap: 8px;">
                <span class="material-symbols-outlined" style="color: #16a34a; font-size: 22px;">person_add</span>
                <h3 style="font-size: 16px; font-weight: 600; color: #0f172a; margin: 0;">Crear Usuario</h3>
              </div>
              <button type="button" (click)="closeCreateUserModal()" style="background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 20px;">
                <span class="material-symbols-outlined">close</span>
              </button>
            </div>

            @if (createUserError()) {
              <div style="padding: 8px 12px; background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; border-radius: 8px; font-size: 12px; margin-bottom: 14px;">{{ createUserError() }}</div>
            }

            <div style="display: flex; flex-direction: column; gap: 12px;">
              <div>
                <label style="font-size: 11px; font-weight: 500; color: #475569; display: block; margin-bottom: 3px;">Username <span style="color:#dc2626;">*</span></label>
                <input type="text" [(ngModel)]="newUserForm.username" placeholder="usuario.ejemplo"
                  style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
              </div>
              <div>
                <label style="font-size: 11px; font-weight: 500; color: #475569; display: block; margin-bottom: 3px;">Email <span style="color:#dc2626;">*</span></label>
                <input type="email" [(ngModel)]="newUserForm.email" placeholder="correo@hotel.com"
                  style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
              </div>
              <div>
                <label style="font-size: 11px; font-weight: 500; color: #475569; display: block; margin-bottom: 3px;">Nombre visible</label>
                <input type="text" [(ngModel)]="newUserForm.displayName" placeholder="Nombre Completo"
                  style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
              </div>
              <div>
                <label style="font-size: 11px; font-weight: 500; color: #475569; display: block; margin-bottom: 3px;">Contraseña <span style="color:#dc2626;">*</span></label>
                <input [type]="showPassword() ? 'text' : 'password'" [(ngModel)]="newUserForm.password" placeholder="Mínimo 6 caracteres"
                  style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none;" />
                <label style="display: flex; align-items: center; gap: 4px; margin-top: 3px; font-size: 11px; color: #94a3b8; cursor: pointer;">
                  <input type="checkbox" [checked]="showPassword()" (change)="showPassword.set($any($event.target).checked)" style="width: 12px; height: 12px;" />
                  Mostrar contraseña
                </label>
              </div>
              <div>
                <label style="font-size: 11px; font-weight: 500; color: #475569; display: block; margin-bottom: 3px;">Rol <span style="color:#dc2626;">*</span></label>
                <select [(ngModel)]="newUserForm.role"
                  style="width: 100%; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; box-sizing: border-box; outline: none; background: white;">
                  @for (r of hotelRoles; track r.value) {
                    <option [value]="r.value">{{ r.label }}</option>
                  }
                </select>
              </div>
            </div>

            <div style="display: flex; gap: 10px; margin-top: 20px; justify-content: flex-end;">
              <button type="button" (click)="closeCreateUserModal()"
                style="padding: 9px 18px; background: white; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; cursor: pointer;">
                Cancelar
              </button>
              <button type="button" (click)="submitCreateUser()" [disabled]="createUserSaving()"
                style="padding: 9px 18px; background: #16a34a; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer;">
                @if (createUserSaving()) {
                  <span class="material-symbols-outlined spinning" style="font-size: 14px; vertical-align: middle;">sync</span>
                  Creando...
                } @else {
                  Crear usuario
                }
              </button>
            </div>
          </div>
        </div>
      }
  `,
  styles: [`.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); border: 0; }`]
})
export class EmployeeOnboardingPageComponent {
  private readonly hrApi = inject(HrApiService);
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);
  private readonly router = inject(Router);
  readonly propCtx = inject(PropertyContextService);

  readonly step = signal(1);
  readonly submitting = signal(false);
  readonly error = signal<string | null>(null);
  readonly success = signal<string | null>(null);

  readonly steps = [
    { num: 1, label: 'Información Personal' },
    { num: 2, label: 'Detalles de Empleo' },
    { num: 3, label: 'Confirmación' },
    { num: 4, label: 'Registro' },
  ];

  // ── User search dropdown ──
  readonly usersSearchResults = signal<any[]>([]);
  readonly userSearchFilter = signal('');
  readonly userDropdownOpen = signal(false);
  readonly selectedUser = signal<{ user_id: string; username: string; email: string; display_name: string; primary_role: string } | null>(null);
  readonly usersLoading = signal(false);

  readonly filteredUsers = computed(() => {
    const q = this.userSearchFilter().toLowerCase().trim();
    const users = this.usersSearchResults();
    if (!q) return users;
    return users.filter(u =>
      (u.username || '').toLowerCase().includes(q) ||
      (u.email || '').toLowerCase().includes(q) ||
      (u.display_name || '').toLowerCase().includes(q)
    );
  });

  readonly selectedUserLabel = computed(() => {
    const u = this.selectedUser();
    if (!u) return '';
    const name = u.display_name || u.username || '';
    const email = u.email || '';
    return email ? `${name} (${email})` : name;
  });

  searchUsers(): void {
    // Cache: skip API call if we already have results
    if (this.usersSearchResults().length > 0) return;
    this.usersLoading.set(true);
    this.http.get<any>(`${this.apiConfig.baseUrl}/admin/users`, { withCredentials: true }).subscribe({
      next: (res) => {
        this.usersSearchResults.set(res.users || []);
        this.usersLoading.set(false);
      },
      error: () => {
        this.usersSearchResults.set([]);
        this.usersLoading.set(false);
      },
    });
  }

  selectUser(user: any): void {
    this.selectedUser.set(user);
    this.userDropdownOpen.set(false);
    this.userSearchFilter.set('');
  }

  clearUser(): void {
    this.selectedUser.set(null);
  }

  readonly userHovered = signal<string | null>(null);

  closeUserDropdown(): void {
    window.setTimeout(() => this.userDropdownOpen.set(false), 200);
  }

  // ── Create User Quick Modal ──
  readonly showCreateUserModal = signal(false);
  readonly createUserSaving = signal(false);
  readonly createUserError = signal('');
  readonly showPassword = signal(false);

  readonly hotelRoles = [
    { value: 'hotel_partner', label: 'Hotel Partner' },
    { value: 'gerente_hotel', label: 'Gerente de Hotel' },
    { value: 'revenue_manager', label: 'Revenue Manager' },
    { value: 'marketing_hotelero', label: 'Marketing Hotelero' },
    { value: 'maintenance', label: 'Mantenimiento' },
  ];

  readonly newUserForm = {
    username: '',
    email: '',
    displayName: '',
    password: '',
    role: 'gerente_hotel',
  };

  openCreateUserModal(): void {
    this.createUserError.set('');
    this.createUserSaving.set(false);
    this.showPassword.set(false);
    this.newUserForm.username = this.form.email || '';
    this.newUserForm.email = this.form.email || '';
    this.newUserForm.displayName = this.form.fullName || '';
    this.newUserForm.password = '';
    this.newUserForm.role = 'gerente_hotel';
    this.showCreateUserModal.set(true);
  }

  closeCreateUserModal(): void {
    this.showCreateUserModal.set(false);
  }

  submitCreateUser(): void {
    const { username, email, displayName, password, role } = this.newUserForm;
    if (!username.trim() || !email.trim() || !password.trim()) {
      this.createUserError.set('Username, email y contraseña son obligatorios.');
      return;
    }
    if (password.length < 6) {
      this.createUserError.set('La contraseña debe tener al menos 6 caracteres.');
      return;
    }

    this.createUserSaving.set(true);
    this.createUserError.set('');

    this.http.post<any>(`${this.apiConfig.baseUrl}/admin/ownership/users`, {
      username: username.trim(),
      email: email.trim().toLowerCase(),
      password: password,
      primary_role: role,
      display_name: displayName.trim() || username.trim(),
      assigned_hotels: [],
    }, { withCredentials: true }).subscribe({
      next: (result) => {
        this.createUserSaving.set(false);
        if (result.ok && result.user) {
          // Auto-select the newly created user
          this.selectedUser.set(result.user);
          // Invalidate users cache so next search fetches fresh list
          this.usersSearchResults.set([]);
          this.closeCreateUserModal();
        } else {
          this.createUserError.set(result.message || 'Error al crear usuario.');
        }
      },
      error: (err) => {
        this.createUserSaving.set(false);
        this.createUserError.set(err?.error?.detail || err?.message || 'Error al crear usuario.');
      },
    });
  }

  readonly documentChecklist = signal<{ key: string; icon: string; label: string; status: 'pending' | 'completed'; filename: string }[]>([
    { key: 'id_passport', icon: 'badge', label: 'Copia de ID / Pasaporte', status: 'pending', filename: '' },
    { key: 'contract', icon: 'description', label: 'Contrato Firmado', status: 'pending', filename: '' },
    { key: 'tax_form', icon: 'receipt_long', label: 'Formulario de Impuestos', status: 'pending', filename: '' },
    { key: 'certificate', icon: 'school', label: 'Certificado de Estudios', status: 'pending', filename: '' },
  ]);

  form = {
    fullName: '',
    idDocument: '',
    phone: '',
    email: '',
    address: '',
    department: '',
    position: '',
    hireDate: '',
    salary: null as number | null,
    emergencyContact: '',
    emergencyPhone: '',
    notes: '',
    propId: this.propCtx.currentPropId() || null as number | null,
    replacesEmployee: false,
    replacesEmployeeId: '',
    transferShifts: false,
    transferPermissions: false,
    transferTasks: false,
  };

  /** Whether the current user already has a property selected — auto-assign to that hotel */
  get hasCurrentHotel(): boolean {
    return (this.propCtx.currentPropId() ?? 0) > 0 || (this.form.propId ?? 0) > 0;
  }

  onHotelSelected(event: { propId: number; label: string }) {
    this.form.propId = event.propId || null;
  }

  uploadDocument(key: string) {
    // En un entorno real esto abriría un file picker y subiría el archivo al backend
    // Por ahora simulamos la subida
    this.documentChecklist.update(list =>
      list.map(d => d.key === key ? { ...d, status: 'completed' as const, filename: `${key}_${Date.now()}.pdf` } : d)
    );
  }

  nextStep() { this.step.update(s => Math.min(s + 1, 4)); }
  prevStep() { this.step.update(s => Math.max(s - 1, 1)); }

  submit() {
    this.submitting.set(true);
    this.error.set(null);

    const payload: any = {
      full_name: this.form.fullName,
      id_document: this.form.idDocument,
      phone: this.form.phone,
      email: this.form.email,
      address: this.form.address,
      department: this.form.department,
      position: this.form.position,
      hire_date: this.form.hireDate,
      salary: this.form.salary,
      emergency_contact: this.form.emergencyContact,
      emergency_phone: this.form.emergencyPhone,
      notes: this.form.notes,
      prop_id: this.form.propId,
      user_id: this.selectedUser()?.user_id || null,
    };

    if (this.form.replacesEmployee && this.form.replacesEmployeeId) {
      payload.replaces_employee_id = this.form.replacesEmployeeId;
      payload.transfer_shifts = this.form.transferShifts;
      payload.transfer_permissions = this.form.transferPermissions;
      payload.transfer_tasks = this.form.transferTasks;
    }

    this.hrApi.createEmployee(payload).subscribe({
      next: (result: any) => {
        this.submitting.set(false);
        this.success.set(`Empleado registrado correctamente. ID: ${(result as any).id || ''}`);
        setTimeout(() => this.router.navigate(['/management/hr', (result as any).id]), 1500);
      },
      error: (err) => {
        this.error.set(err?.error?.detail || 'Error al registrar empleado');
        this.submitting.set(false);
      },
    });
  }
}
