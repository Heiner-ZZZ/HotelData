import { ChangeDetectionStrategy, Component, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';

import { PropertySelectorComponent } from '../../../../shared/ui/property-selector/property-selector';
import { PropertyContextService } from '../../../../shared/services/property-context.service';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';
import { HrApiService } from '../../services/hr-api.service';

@Component({
  selector: 'app-employee-list-page',
  standalone: true,
  imports: [RouterLink, FormsModule, PageHeaderComponent, PropertySelectorComponent, LoadingStateComponent, EmptyStateComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="employee-page" style="max-width: 1100px; margin: 0 auto; padding: 24px;">
      <app-page-header
        eyebrow="RRHH - Staff Directory"
        title="Directorio de Empleados"
        description="Consulta, busca y gestiona el personal del hotel."
      />

      <app-property-selector
        [selectedPropId]="propertyCtx.currentPropId()"
        [selectedLabel]="propertyCtx.currentPropLabel()"
        (propIdChange)="onPropSelected($event)"
      />

      <div style="display: flex; gap: 10px; align-items: center; margin-bottom: 20px; flex-wrap: wrap;">
        <div style="flex: 1; min-width: 200px; position: relative;">
          <span class="material-symbols-outlined" style="position: absolute; left: 10px; top: 50%; transform: translateY(-50%); font-size: 18px; color: #94a3b8;">search</span>
          <input type="text" [(ngModel)]="searchTerm" (input)="onSearch()" placeholder="Buscar por nombre, documento o email..."
            style="width: 100%; padding: 8px 12px 8px 34px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; font-family: inherit; box-sizing: border-box; outline: none;" />
        </div>
        <select [(ngModel)]="selectedDepartment" (change)="onFilterChange()"
          style="padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; font-family: inherit; color: #475569; background: white; min-width: 160px; cursor: pointer; outline: none;">
          <option value="">Todos los departamentos</option>
          @for (dept of departments(); track dept.id) {
            <option [value]="dept.name">{{ dept.name }}</option>
          }
        </select>
        <select [(ngModel)]="selectedStatus" (change)="onFilterChange()"
          style="padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 13px; font-family: inherit; color: #475569; background: white; min-width: 130px; cursor: pointer; outline: none;">
          <option value="">Todos los estados</option>
          <option value="true">Activos</option>
          <option value="false">Inactivos</option>
        </select>
        <button type="button" (click)="clearFilters()"
          style="padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 12px; font-family: inherit; color: #64748b; background: white; cursor: pointer;">
          <span class="material-symbols-outlined" style="font-size: 14px; vertical-align: middle;">filter_list_off</span>
        </button>
        <button type="button" (click)="createEmployee()"
          style="display: flex; align-items: center; gap: 6px; padding: 8px 16px; background: #2563eb; color: white; border: none; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer;">
          <span class="material-symbols-outlined" style="font-size: 16px;">person_add</span>
          Nuevo Empleado
        </button>
      </div>

      @switch (viewState()) {
        @case ('loading') { <app-loading-state label="Cargando empleados..." /> }
        @case ('empty') { <app-empty-state icon="group" title="Sin empleados" description="No hay empleados registrados. Crea el primer registro." /> }
        @case ('error') { <app-empty-state icon="error" title="Error" description="No se pudo cargar el directorio." /> }
        @default {
          @if (data(); as vm) {
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden;">
              <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
                <thead>
                  <tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                    <th style="padding: 12px 16px; text-align: left; font-weight: 600; color: #475569;">Nombre</th>
                    <th style="padding: 12px 16px; text-align: left; font-weight: 600; color: #475569;">Departamento</th>
                    <th style="padding: 12px 16px; text-align: left; font-weight: 600; color: #475569;">Puesto</th>
                    <th style="padding: 12px 16px; text-align: left; font-weight: 600; color: #475569;">Email</th>
                    <th style="padding: 12px 16px; text-align: left; font-weight: 600; color: #475569;">Estado</th>
                    <th style="padding: 12px 16px; text-align: left; font-weight: 600; color: #475569;">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  @for (emp of vm.items; track emp.id) {
                    <tr style="border-bottom: 1px solid #f1f5f9;">
                      <td style="padding: 12px 16px; font-weight: 500;">
                        <a [routerLink]="['/management/hr', emp.id]" style="color: #2563eb; text-decoration: none;">{{ emp.fullName }}</a>
                      </td>
                      <td style="padding: 12px 16px; color: #475569;">{{ emp.department || '—' }}</td>
                      <td style="padding: 12px 16px; color: #475569;">{{ emp.position || '—' }}</td>
                      <td style="padding: 12px 16px; color: #64748b;">{{ emp.email || '—' }}</td>
                      <td style="padding: 12px 16px;">
                        <span [style]="emp.isActive ? 'background:#f0fdf4;color:#166534;' : 'background:#fef2f2;color:#991b1b;'"
                          style="padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600;">
                          {{ emp.isActive ? 'Activo' : 'Inactivo' }}
                        </span>
                      </td>
                      <td style="padding: 12px 16px;">
                        <a [routerLink]="['/management/hr', emp.id]" style="display: flex; align-items: center; gap: 4px; color: #2563eb; text-decoration: none; font-size: 12px;">
                          <span class="material-symbols-outlined" style="font-size: 14px;">visibility</span> Ver
                        </a>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
            @if (vm.totalPages > 1) {
              <div style="display: flex; justify-content: center; gap: 8px; margin-top: 16px;">
                <button (click)="goToPage(vm.page - 1)" [disabled]="!vm.hasPrev"
                  style="padding: 6px 12px; border: 1px solid #e2e8f0; border-radius: 6px; background: white; font-size: 12px; cursor: pointer; &:disabled { opacity: 0.4; }">
                  Anterior
                </button>
                <span style="font-size: 12px; color: #64748b; padding: 6px 12px;">Página {{ vm.page }} de {{ vm.totalPages }}</span>
                <button (click)="goToPage(vm.page + 1)" [disabled]="!vm.hasNext"
                  style="padding: 6px 12px; border: 1px solid #e2e8f0; border-radius: 6px; background: white; font-size: 12px; cursor: pointer; &:disabled { opacity: 0.4; }">
                  Siguiente
                </button>
              </div>
            }
          }
        }
      }
    </div>
  `
})
export class EmployeeListPageComponent implements OnInit {
  private readonly destroyRef = inject(DestroyRef);
  private readonly hrApi = inject(HrApiService);
  private readonly router = inject(Router);
  readonly propertyCtx = inject(PropertyContextService);
  private searchTimeout: any;

  readonly viewState = signal<'loading' | 'success' | 'empty' | 'error'>('loading');
  readonly data = signal<any>(null);
  readonly searchTerm = signal('');
  readonly selectedDepartment = signal('');
  readonly selectedStatus = signal('');
  readonly currentPage = signal(1);
  readonly departments = signal<{ id: string; name: string }[]>([]);

  ngOnInit() {
    this.loadDepartments();
    this.loadEmployees();
  }

  private loadDepartments() {
    this.hrApi.getDepartments()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (depts) => this.departments.set(depts),
        error: () => {},
      });
  }

  private resolveIsActive(): boolean | undefined {
    const val = this.selectedStatus();
    if (val === 'true') return true;
    if (val === 'false') return false;
    return undefined;
  }

  onPropSelected(event: { propId: number; label: string }) {
    if (!event.propId) this.propertyCtx.clear();
    else this.propertyCtx.setProperty(event.propId, event.label || `Propiedad #${event.propId}`);
    this.currentPage.set(1);
    this.loadEmployees();
  }

  loadEmployees() {
    this.viewState.set('loading');
    this.hrApi.getEmployees(
      this.searchTerm() || undefined,
      this.selectedDepartment() || undefined,
      this.resolveIsActive(),
      this.currentPage(),
      this.propertyCtx.currentPropId() || undefined,
    )
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.data.set(result);
          this.viewState.set(result.items.length > 0 ? 'success' : 'empty');
        },
        error: () => this.viewState.set('error'),
      });
  }

  onSearch() {
    clearTimeout(this.searchTimeout);
    this.searchTimeout = setTimeout(() => {
      this.currentPage.set(1);
      this.loadEmployees();
    }, 300);
  }

  onFilterChange() {
    this.currentPage.set(1);
    this.loadEmployees();
  }

  clearFilters() {
    this.selectedDepartment.set('');
    this.selectedStatus.set('');
    this.currentPage.set(1);
    this.loadEmployees();
  }

  goToPage(page: number) {
    this.currentPage.set(page);
    this.loadEmployees();
  }

  createEmployee() {
    void this.router.navigate(['/management/hr/onboarding']);
  }
}
