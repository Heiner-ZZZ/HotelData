import { Injectable, computed, inject } from '@angular/core';
import { httpResource } from '@angular/common/http';

import type { SystemPermissionsResponseDto } from '../models/system-permissions.dto';
import type { SystemPermissionsViewModel } from '../models/system-permissions.model';
import { mapSystemPermissionsResponse } from '../mappers/system-permissions.mapper';

@Injectable({ providedIn: 'root' })
export class SystemPermissionsContextService {
  readonly overviewResource = httpResource<SystemPermissionsViewModel>(
    () => '/api/admin/permissions',
    { parse: (dto) => mapSystemPermissionsResponse(dto as SystemPermissionsResponseDto) },
  );

  readonly viewState = computed<'loading' | 'error' | 'empty' | 'success'>(() => {
    if (this.overviewResource.isLoading()) return 'loading';
    if (this.overviewResource.error()) return 'error';
    const value = this.overviewResource.value();
    if (!value) return 'loading';
    return value.roles.length || value.permissions.length ? 'success' : 'empty';
  });
}
