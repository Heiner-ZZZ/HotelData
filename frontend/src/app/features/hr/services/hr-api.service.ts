import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapEmployeeDetail, mapEmployeeList, mapHrDashboard, mapEmployeePortal } from '../mappers/hr.mapper';
import type { EmployeeDetailDto, EmployeeListDto, EmployeePortalDto } from '../models/hr.dto';

@Injectable({ providedIn: 'root' })
export class HrApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getDashboard() {
    return this.http.get<any>(`${this.apiConfig.baseUrl}/hr/dashboard`, { withCredentials: true })
      .pipe(map(dto => mapHrDashboard(dto)));
  }

  getEmployees(search?: string, department?: string, isActive?: boolean, page: number = 1, propId?: number) {
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

  createEmployee(payload: any) {
    return this.http.post(`${this.apiConfig.baseUrl}/hr`, payload, { withCredentials: true });
  }

  updateEmployee(id: string, payload: any) {
    return this.http.put(`${this.apiConfig.baseUrl}/hr/${id}`, payload, { withCredentials: true });
  }

  deleteEmployee(id: string) {
    return this.http.delete(`${this.apiConfig.baseUrl}/hr/${id}`, { withCredentials: true });
  }

  getDepartments() {
    return this.http.get<any[]>(`${this.apiConfig.baseUrl}/hr/departments`, { withCredentials: true });
  }

  // ─── My Portal (self-service redirect) ───

  getMyPortal() {
    return this.http.get<{ employee_id: string; full_name: string; portal_url: string }>(
      `${this.apiConfig.baseUrl}/hr/my-portal`,
      { withCredentials: true },
    );
  }

  // ─── Portal ───

  getPortal(employeeId: string) {
    return this.http.get<EmployeePortalDto>(`${this.apiConfig.baseUrl}/hr/portal/${employeeId}`, { withCredentials: true })
      .pipe(map(dto => mapEmployeePortal(dto)));
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
}
