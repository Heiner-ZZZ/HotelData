import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapEmployeeDetail, mapEmployeeList, mapHrDashboard, mapEmployeePortal, mapAttendanceResponse, mapShiftList, mapPortalTasks } from '../mappers/hr.mapper';
import type { AttendanceResponseDto, DepartmentListDto, EmployeeCreateDto, EmployeeDetailDto, EmployeeListDto, EmployeePortalDto, EmployeeShiftDto, EmployeeUpdateDto, HrDashboardDto, PortalTasksDto, ReplacementCandidateListDto, ShiftCreateDto, ShiftListDto } from '../models/hr.dto';

@Injectable({ providedIn: 'root' })
export class HrApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getDashboard() {
    return this.http.get<HrDashboardDto>(`${this.apiConfig.baseUrl}/hr/dashboard`, { withCredentials: true })
      .pipe(map(dto => mapHrDashboard(dto)));
  }

  getEmployees(search?: string, department?: string, isActive?: boolean, page = 1, propId?: number) {
    let params = new HttpParams().set('page', String(page));
    if (search) params = params.set('search', search);
    if (department) params = params.set('department', department);
    if (isActive !== undefined) params = params.set('is_active', String(isActive));
    if (propId) params = params.set('prop_id', String(propId));
    return this.http.get<EmployeeListDto>(`${this.apiConfig.baseUrl}/hr`, { params, withCredentials: true })
      .pipe(map(dto => mapEmployeeList(dto)));
  }

  getEmployee(id: string) {
    return this.http.get<EmployeeDetailDto>(`${this.apiConfig.baseUrl}/hr/${id}`, { withCredentials: true })
      .pipe(map(dto => mapEmployeeDetail(dto)));
  }

  createEmployee(payload: EmployeeCreateDto) {
    return this.http.post<EmployeeDetailDto>(`${this.apiConfig.baseUrl}/hr`, payload, { withCredentials: true });
  }

  updateEmployee(id: string, payload: EmployeeUpdateDto) {
    return this.http.put<EmployeeDetailDto>(`${this.apiConfig.baseUrl}/hr/${id}`, payload, { withCredentials: true });
  }

  deleteEmployee(id: string) {
    return this.http.delete(`${this.apiConfig.baseUrl}/hr/${id}`, { withCredentials: true });
  }

  getDepartments() {
    return this.http.get<DepartmentListDto>(`${this.apiConfig.baseUrl}/hr/departments`, { withCredentials: true })
      .pipe(map(response => response.items ?? []));
  }

  getReplacementCandidates(propId: number) {
    return this.http.get<ReplacementCandidateListDto>(
      `${this.apiConfig.baseUrl}/hr/replacement-candidates`,
      { params: new HttpParams().set('prop_id', String(propId)), withCredentials: true },
    );
  }

  // ─── My Portal (self-service redirect) ───

  getMyPortal() {
    return this.http.get<{ employee_id: string; full_name: string; portal_url: string }>(
      `${this.apiConfig.baseUrl}/hr/my-portal`,
      { withCredentials: true },
    );
  }

  // ─── Portal ───

  getPortal(employeeId: string, weekStart?: string) {
    let params = new HttpParams();
    if (weekStart) params = params.set('week_start', weekStart);
    return this.http.get<EmployeePortalDto>(
      `${this.apiConfig.baseUrl}/hr/portal/${employeeId}`,
      { params, withCredentials: true },
    ).pipe(map(dto => mapEmployeePortal(dto)));
  }

  shiftCheckIn(shiftId: string, employeeId: string, notes?: string) {
    return this.http.post(`${this.apiConfig.baseUrl}/hr/shifts/${shiftId}/check-in`, {
      employee_id: employeeId,
      notes: notes || '',
    }, { withCredentials: true });
  }

  shiftCheckOut(shiftId: string, employeeId: string, notes?: string) {
    return this.http.post(`${this.apiConfig.baseUrl}/hr/shifts/${shiftId}/check-out`, {
      employee_id: employeeId,
      notes: notes || '',
    }, { withCredentials: true });
  }

  // ─── Shift Schedule ───

  getShifts(employeeId?: string, date?: string, dateFrom?: string, dateTo?: string, page = 1) {
    let params = new HttpParams().set('page', String(page));
    if (employeeId) params = params.set('employee_id', employeeId);
    if (date) params = params.set('date', date);
    if (dateFrom) params = params.set('date_from', dateFrom);
    if (dateTo) params = params.set('date_to', dateTo);
    return this.http.get<ShiftListDto>(`${this.apiConfig.baseUrl}/hr/shifts`, { params, withCredentials: true })
      .pipe(map(dto => mapShiftList(dto)));
  }

  createShift(payload: ShiftCreateDto) {
    return this.http.post<EmployeeShiftDto>(`${this.apiConfig.baseUrl}/hr/shifts`, payload, { withCredentials: true });
  }

  updateShift(shiftId: string, payload: ShiftCreateDto) {
    return this.http.put<EmployeeShiftDto>(`${this.apiConfig.baseUrl}/hr/shifts/${shiftId}`, payload, { withCredentials: true });
  }

  deleteShift(shiftId: string) {
    return this.http.delete(`${this.apiConfig.baseUrl}/hr/shifts/${shiftId}`, { withCredentials: true });
  }

  // ─── Attendance History ───

  getAttendance(employeeId: string, month?: string) {
    let params = new HttpParams();
    if (month) params = params.set('month', month);
    return this.http.get<AttendanceResponseDto>(
      `${this.apiConfig.baseUrl}/hr/${employeeId}/attendance`,
      { params, withCredentials: true },
    ).pipe(map(dto => mapAttendanceResponse(dto)));
  }

  // ─── Portal Tasks & Operations ───

  getPortalTasks(employeeId: string) {
    return this.http.get<PortalTasksDto>(
      `${this.apiConfig.baseUrl}/hr/portal/${employeeId}/tasks`,
      { withCredentials: true },
    ).pipe(map(dto => mapPortalTasks(dto)));
  }

  /** Quick action: start a housekeeping task (pending → in_progress) */
  startTask(taskId: string, payload: Record<string, unknown>) {
    return this.http.put(
      `${this.apiConfig.baseUrl}/housekeeping/tasks/${taskId}`, payload,
      { withCredentials: true },
    );
  }

  /** Quick action: complete a housekeeping task */
  completeTask(taskId: string) {
    return this.http.post(
      `${this.apiConfig.baseUrl}/housekeeping/tasks/${taskId}/complete`,
      { note: '' },
      { withCredentials: true },
    );
  }
}
