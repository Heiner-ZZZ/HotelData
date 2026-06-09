te puedes guir de las skill que te he puesto?
y del agent? no guardes mucha memoria de eso por que igual LO TIENES A MANO PARA LEERLO A CADA MOMENTO SIN TENER QUE GUARDAR TODO EN VENTANA DE CONTEXTO, ENTENDIDO? EMPIEZA A CREAR LO INICIAL Y A MIGRAR
ORGANIZA POR RESPONSABILIDAD.
-

frontend/
├─ angular.json
├─ package.json
├─ src/
│  ├─ main.ts
│  ├─ styles.scss
│  ├─ index.html
│  └─ app/
│     ├─ app.ts
│     ├─ app.html
│     ├─ app.scss
│     ├─ app.routes.ts
│     │
│     ├─ core/
│     │  ├─ api/
│     │  │  ├─ api.config.ts
│     │  │  ├─ api-error.model.ts
│     │  │  └─ http-error.interceptor.ts
│     │  ├─ auth/
│     │  │  ├─ auth.service.ts
│     │  │  ├─ auth.guard.ts
│     │  │  └─ auth.models.ts
│     │  └─ layout/
│     │     ├─ public-shell/
│     │     │  ├─ public-shell.ts
│     │     │  ├─ public-shell.html
│     │     │  └─ public-shell.scss
│     │     └─ admin-shell/
│     │        ├─ admin-shell.ts
│     │        ├─ admin-shell.html
│     │        └─ admin-shell.scss
│     │
│     ├─ shared/
│     │  ├─ ui/
│     │  │  ├─ page-header/
│     │  │  │  ├─ page-header.ts
│     │  │  │  ├─ page-header.html
│     │  │  │  └─ page-header.scss
│     │  │  ├─ empty-state/
│     │  │  ├─ error-state/
│     │  │  ├─ loading-state/
│     │  │  └─ status-badge/
│     │  ├─ pipes/
│     │  ├─ utils/
│     │  │  ├─ currency-format.util.ts
│     │  │  └─ date-format.util.ts
│     │  └─ types/
│     │
│     └─ features/
│        ├─ admin/
│        │  ├─ pages/
│        │  │  └─ dashboard-page/
│        │  │     ├─ dashboard-page.ts
│        │  │     ├─ dashboard-page.html
│        │  │     └─ dashboard-page.scss
│        │  ├─ components/
│        │  │  ├─ metric-card/
│        │  │  ├─ occupancy-summary/
│        │  │  └─ recent-reservations/
│        │  └─ admin.routes.ts
│        │
│        ├─ hotel-search/
│        │  ├─ pages/
│        │  │  └─ hotel-search-page/
│        │  │     ├─ hotel-search-page.ts
│        │  │     ├─ hotel-search-page.html
│        │  │     └─ hotel-search-page.scss
│        │  ├─ components/
│        │  │  ├─ hotel-card/
│        │  │  ├─ filter-sidebar/
│        │  │  ├─ mobile-filter-drawer/
│        │  │  └─ sort-control/
│        │  ├─ services/
│        │  │  └─ hotel-search-api.service.ts
│        │  ├─ models/
│        │  │  ├─ hotel-search.model.ts
│        │  │  └─ hotel-search.dto.ts
│        │  ├─ mappers/
│        │  │  └─ hotel-search.mapper.ts
│        │  └─ hotel-search.routes.ts
│        │
│        ├─ hotel-detail/
│        │  ├─ pages/
│        │  ├─ components/
│        │  ├─ services/
│        │  ├─ models/
│        │  ├─ mappers/
│        │  └─ hotel-detail.routes.ts
│        │
│        ├─ reservations/
│        │  ├─ pages/
│        │  ├─ components/
│        │  ├─ services/
│        │  ├─ models/
│        │  ├─ mappers/
│        │  └─ reservations.routes.ts
│        │
│        ├─ properties/
│        │  ├─ pages/
│        │  ├─ components/
│        │  ├─ services/
│        │  ├─ models/
│        │  ├─ mappers/
│        │  └─ properties.routes.ts
│        │
│        └─ availability/
│           ├─ pages/
│           ├─ components/
│           ├─ services/
│           ├─ models/
│           ├─ mappers/
│           └─ availability.routes.ts

CODEX: 

Sí, me guío por esas skills y por AGENTS.md, y no voy a “memorizar de más”: los voy leyendo cuando haga falta y trabajo con eso a mano. Primero abro lo mínimo necesario y luego empiezo a dejar la base Angular organizada por responsabilidad y la primera migración inicial.

El sandbox está haciendo un pequeño berrinche al refrescar, así que reintento con lecturas puntuales. Quiero sacar solo las reglas útiles para no inflar contexto y empezar a construir enseguida.

Voy a probar una lectura simple fuera del atasco del refresh. En cuanto tenga eso, paso directo a crear la estructura y no te hago esperar con teoría.

Ya tengo AGENTS.md. Ahora saco solo lo esencial de las skills de Angular, frontend y migración Jinja para seguir esas reglas sin cargar ruido innecesario.

Voy a usar tres guías en este orden: angular-senior, frontend-engineering y jinja-to-angular-migration. Ahora inspecciono el Angular recién creado y un par de rutas/templates legacy para armar la base correcta antes de mover la primera pantalla.

Ya vi dos cosas clave: Angular está en standalone moderno y el dashboard legacy es un buen primer candidato porque nos deja montar layout, routing y estados sin tocar auth todavía. Sigo con una lectura cortita de la app Angular actual y de algunos servicios legacy para modelar la primera pantalla con responsabilidades limpias.

Ya tengo el mapa técnico suficiente para empezar bien. Antes de editar voy a hacer dos cosas concretas: crear la arquitectura Angular por responsabilidad que pediste, y conectar una primera migración real del dashboard usando API FastAPI tipada en vez de copiar lógica al frontend.

El dashboard ya está claro y el buscador legacy también. Voy a tocar una última pieza del backend de auth para no inventar contratos, y después entro a editar: estructura Angular, shells, routing, servicio API y primer dashboard migrado.

Ya voy a entrar a los edits. Voy a crear la base completa por responsabilidades y dejar una primera migración funcional del dashboard con API real; el resto de features quedará scaffolded, no mezclado ni amontonado.

El sandbox volvió a tropezarse justo al crear carpetas. Lo reintento con privilegio de lectura/escritura local para no perder el hilo de implementación.


Created 73 files, edited 7 files
Created file
frontend-migration-map.md
+29
-0

# Frontend Migration Map

## Objective

Progressively migrate the legacy FastAPI + Jinja2 frontend into `frontend/` with Angular, while preserving the current backend routes and ETL behavior.

## Status Snapshot

| Area | Legacy route | Legacy template | Angular route | Angular feature | Backend endpoint | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Admin dashboard | `/dashboard` | `src/app/templates/dashboard/index.html` | `/admin` | `features/admin` | `GET /api/dashboard/overview` | in_progress | First real migration. Legacy route remains active. |
| Hotel search | `/hotels/search` | `src/app/templates/hotels/search.html` | `/search` | `features/hotel-search` | pending JSON endpoint | scaffolded | Needs typed search API before full migration. |
| Hotel detail | `/hotels/{prop_id}` | `src/app/templates/hotels/detail.html` | `/hotels/:hotelId` | `features/hotel-detail` | pending JSON endpoint | scaffolded | Route structure prepared. |
| Reservations | `/reservations` | `src/app/templates/reservations/*.html` | `/reservations` | `features/reservations` | pending endpoint review | scaffolded | Awaiting API boundary review. |
| Properties admin | `/partner/hotels` | `src/app/templates/partner/*.html` | `/admin/properties` | `features/properties` | pending endpoint review | scaffolded | Candidate for second admin migration wave. |
| Availability admin | `/partner/inventory` and related | `src/app/templates/partner/inventory.html` | `/admin/availability` | `features/availability` | pending endpoint review | scaffolded | Requires inventory/rates API analysis. |

## Immediate Decisions

- Angular is organized by `core`, `shared`, and `features`.
- FastAPI remains the source of truth for data and auth/session.
- New Angular data access must use typed API services.
- Legacy Jinja views are preserved during migration.

## Risks

- Some legacy screens return HTML only and still need JSON API endpoints.
- Session auth is cookie-based, so Angular must preserve `withCredentials`.
- Running Angular on port `4200` will need proxy or CORS alignment with FastAPI on `8000`.
Edited file
angular.json
+6
-3

        },
        "serve": {
          "builder": "@angular/build:dev-server",
          "configurations": {
        "serve": {
          "builder": "@angular/build:dev-server",
          "options": {
            "proxyConfig": "proxy.conf.json"
          },
          "configurations": {
            "production": {
Created file
proxy.conf.json
+7
-0

{
  "/api": {
    "target": "http://localhost:8000",
    "secure": false,
    "changeOrigin": true
  }
}
Edited file
routes.py
+9
-0

    )


@router.get("/api/dashboard/overview")
def dashboard_overview_api():
    return {
        "counts": collection_counts(),
        "quality": quality_summary(),
        "overview": dashboard_overview(),
    }
Edited file
main.py
+2
-0

from src.app.modules.auth.routes import router as auth_module_router
from src.app.modules.auth.routes import api_router as auth_api_router
from src.app.modules.auth.routes import web_router as auth_web_router
    app.include_router(auth_module_router)
    app.include_router(auth_api_router)
    app.include_router(users_module_router)
Edited file
routes.py
+24
-0

web_router = APIRouter(prefix="/auth", tags=["auth"])
api_router = APIRouter(prefix="/api/auth", tags=["auth-api"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))
    )


@api_router.get("/me")
def me_api(request: Request):
    db = get_database()
    user, session = get_current_user(db, request.cookies.get(SESSION_COOKIE_NAME))
    if not user:
        return {"authenticated": False, "user": None, "session": None}

    return {
        "authenticated": True,
        "user": {
            "username": user.get("username"),
            "email": user.get("email"),
            "primary_role": user.get("primary_role"),
            "is_active": user.get("is_active", True),
        },
        "session": {
            "token": session.get("token") if session else None,
            "expires_at": session.get("expires_at") if session else None,
            "created_at": session.get("created_at") if session else None,
        },
    }
Edited file
app.config.ts
+20
-11

import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter } from '@angular/router';

import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes)
  ]
};
import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter, withInMemoryScrolling } from '@angular/router';

import { routes } from './app.routes';
import { httpErrorInterceptor } from './core/api/http-error.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideHttpClient(withInterceptors([httpErrorInterceptor])),
    provideRouter(
      routes,
      withInMemoryScrolling({
        scrollPositionRestoration: 'enabled',
        anchorScrolling: 'enabled'
      })
    )
  ]
};
Created file
app.html
+1
-0

<router-outlet />
Edited file
app.routes.ts
+56
-3

import { Routes } from '@angular/router';

export const routes: Routes = [];
import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: 'search'
  },
  {
    path: '',
    loadComponent: () =>
      import('./core/layout/public-shell/public-shell').then((m) => m.PublicShellComponent),
    children: [
      {
        path: 'search',
        loadChildren: () =>
          import('./features/hotel-search/hotel-search.routes').then((m) => m.HOTEL_SEARCH_ROUTES)
      },
      {
        path: 'hotels',
        loadChildren: () =>
          import('./features/hotel-detail/hotel-detail.routes').then((m) => m.HOTEL_DETAIL_ROUTES)
      },
      {
        path: 'reservations',
        loadChildren: () =>
          import('./features/reservations/reservations.routes').then((m) => m.RESERVATIONS_ROUTES)
      }
    ]
  },
  {
    path: 'admin',
    loadComponent: () =>
      import('./core/layout/admin-shell/admin-shell').then((m) => m.AdminShellComponent),
    children: [
      {
        path: '',
        loadChildren: () => import('./features/admin/admin.routes').then((m) => m.ADMIN_ROUTES)
      },
      {
        path: 'properties',
        loadChildren: () =>
          import('./features/properties/properties.routes').then((m) => m.PROPERTIES_ROUTES)
      },
      {
        path: 'availability',
        loadChildren: () =>
          import('./features/availability/availability.routes').then((m) => m.AVAILABILITY_ROUTES)
      }
    ]
  },
  {
    path: '**',
    redirectTo: 'search'
  }
];
Created file
app.scss
+4
-0

:host {
  display: block;
  min-height: 100vh;
}
Edited file
app.ts
+10
-12

import { Component, signal } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  protected readonly title = signal('frontend');
}
import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {}
Created file
api-error.model.ts
+6
-0

export interface ApiError {
  status: number;
  message: string;
  code?: string;
  details?: unknown;
}
Created file
api.config.ts
+12
-0

import { InjectionToken } from '@angular/core';

export interface ApiConfig {
  baseUrl: string;
}

export const API_CONFIG = new InjectionToken<ApiConfig>('API_CONFIG', {
  providedIn: 'root',
  factory: () => ({
    baseUrl: '/api'
  })
});
Created file
http-error.interceptor.ts
+32
-0

import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { throwError } from 'rxjs';

import type { ApiError } from './api-error.model';

export const httpErrorInterceptor: HttpInterceptorFn = (request, next) =>
  next(request).pipe(
    // Keep the interceptor lightweight: normalize transport errors only.
    // Feature services can still add screen-specific handling on top.
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ((source: any) =>
      source.pipe({
        subscribe(subscriber: any) {
          return source.subscribe({
            next: (value: unknown) => subscriber.next(value),
            complete: () => subscriber.complete(),
            error: (error: unknown) => {
              if (error instanceof HttpErrorResponse) {
                const apiError: ApiError = {
                  status: error.status,
                  message: error.error?.message || error.message || 'Unexpected API error',
                  details: error.error
                };
                subscriber.error(apiError);
                return;
              }
              subscriber.error(error);
            }
          });
        }
      })) as never
  );
Created file
auth.guard.ts
+19
-0

import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';

import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAuthenticated()) {
    return true;
  }

  return authService.loadSession().pipe(
    map((state) => (state.authenticated ? true : router.createUrlTree(['/search']))),
    catchError(() => of(router.createUrlTree(['/search'])))
  );
};
Created file
auth.models.ts
+33
-0

export interface AuthUser {
  username: string;
  email: string;
  primaryRole: string;
  isActive: boolean;
}

export interface AuthSession {
  token: string | null;
  expiresAt: string | null;
  createdAt: string | null;
}

export interface AuthState {
  authenticated: boolean;
  user: AuthUser | null;
  session: AuthSession | null;
}

export interface AuthMeDto {
  authenticated: boolean;
  user: {
    username: string;
    email: string;
    primary_role: string;
    is_active: boolean;
  } | null;
  session: {
    token: string | null;
    expires_at: string | null;
    created_at: string | null;
  } | null;
}
Created file
auth.service.ts
+63
-0

import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { catchError, map, of, tap } from 'rxjs';

import { API_CONFIG } from '../api/api.config';
import type { AuthMeDto, AuthState } from './auth.models';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  private readonly authStateSignal = signal<AuthState>({
    authenticated: false,
    user: null,
    session: null
  });

  readonly authState = this.authStateSignal.asReadonly();
  readonly currentUser = computed(() => this.authStateSignal().user);
  readonly isAuthenticated = computed(() => this.authStateSignal().authenticated);

  loadSession() {
    return this.http
      .get<AuthMeDto>(`${this.apiConfig.baseUrl}/auth/me`, { withCredentials: true })
      .pipe(
        map((dto) => this.mapAuthState(dto)),
        tap((state) => this.authStateSignal.set(state)),
        catchError(() => {
          const anonymousState: AuthState = {
            authenticated: false,
            user: null,
            session: null
          };
          this.authStateSignal.set(anonymousState);
          return of(anonymousState);
        })
      );
  }

  private mapAuthState(dto: AuthMeDto): AuthState {
    return {
      authenticated: dto.authenticated,
      user: dto.user
        ? {
            username: dto.user.username,
            email: dto.user.email,
            primaryRole: dto.user.primary_role,
            isActive: dto.user.is_active
          }
        : null,
      session: dto.session
        ? {
            token: dto.session.token,
            expiresAt: dto.session.expires_at,
            createdAt: dto.session.created_at
          }
        : null
    };
  }
}
Created file
admin-shell.html
+16
-0

<div class="admin-shell">
  <aside class="admin-sidebar">
    <a class="brand" routerLink="/admin">HotelData Hub</a>
    <nav aria-label="Navegacion administrativa">
      @for (item of navigation; track item.href) {
        <a routerLinkActive="is-active" [routerLink]="item.href" [routerLinkActiveOptions]="{ exact: item.href === '/admin' }">
          {{ item.label }}
        </a>
      }
    </nav>
  </aside>

  <div class="admin-content">
    <router-outlet />
  </div>
</div>
Created file
admin-shell.scss
+54
-0

.admin-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  background: var(--app-bg);
}

.admin-sidebar {
  padding: 1.5rem;
  border-right: 1px solid var(--app-border);
  background: #132033;
  color: #f8fbff;
}

.brand {
  display: inline-block;
  margin-bottom: 1.5rem;
  color: inherit;
  font-size: 1.125rem;
  font-weight: 700;
  text-decoration: none;
}

nav {
  display: grid;
  gap: 0.5rem;
}

nav a {
  padding: 0.75rem 0.875rem;
  color: rgba(248, 251, 255, 0.76);
  text-decoration: none;
  border-radius: 8px;
}

nav a.is-active {
  color: #ffffff;
  background: rgba(20, 99, 255, 0.22);
}

.admin-content {
  padding: 1.5rem;
}

@media (max-width: 960px) {
  .admin-shell {
    grid-template-columns: 1fr;
  }

  .admin-sidebar {
    border-right: 0;
    border-bottom: 1px solid var(--app-border);
  }
}
Created file
admin-shell.ts
+16
-0

import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-admin-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './admin-shell.html',
  styleUrl: './admin-shell.scss'
})
export class AdminShellComponent {
  readonly navigation = [
    { label: 'Dashboard', href: '/admin' },
    { label: 'Properties', href: '/admin/properties' },
    { label: 'Availability', href: '/admin/availability' }
  ];
}
Created file
public-shell.html
+14
-0

<div class="public-shell">
  <header class="public-header">
    <a class="brand" routerLink="/search">HotelData</a>
    <nav aria-label="Navegacion principal">
      @for (item of navigation; track item.href) {
        <a routerLinkActive="is-active" [routerLink]="item.href">{{ item.label }}</a>
      }
    </nav>
  </header>

  <main class="public-main">
    <router-outlet />
  </main>
</div>
Created file
public-shell.scss
+41
-0

.public-shell {
  min-height: 100vh;
  background: var(--app-bg);
  color: var(--app-text);
}

.public-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.5rem;
  border-bottom: 1px solid var(--app-border);
  background: var(--surface);
}

.brand {
  color: var(--app-text);
  font-size: 1.125rem;
  font-weight: 700;
  text-decoration: none;
}

nav {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

nav a {
  color: var(--muted-text);
  text-decoration: none;
}

nav a.is-active {
  color: var(--accent);
}

.public-main {
  padding: 1.5rem;
}
Created file
public-shell.ts
+16
-0

import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-public-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './public-shell.html',
  styleUrl: './public-shell.scss'
})
export class PublicShellComponent {
  readonly navigation = [
    { label: 'Buscar hoteles', href: '/search' },
    { label: 'Reservas', href: '/reservations' },
    { label: 'Panel admin', href: '/admin' }
  ];
}
Created file
styles.scss
+50
-0

:root {
  --app-bg: #f3f6fb;
  --surface: #ffffff;
  --surface-soft: #eef4ff;
  --app-text: #162033;
  --muted-text: #5f6f87;
  --accent: #1463ff;
  --success: #0f8a60;
  --warning: #c98105;
  --danger: #c93d32;
  --app-border: #d8e0eb;
  --shadow-sm: 0 8px 24px rgba(15, 23, 42, 0.06);
  --shadow-md: 0 18px 42px rgba(15, 23, 42, 0.08);
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

html {
  color-scheme: light;
}

body {
  margin: 0;
  min-width: 320px;
  background: var(--app-bg);
  color: var(--app-text);
  font-family: Inter, "Segoe UI", Arial, sans-serif;
}

button,
input,
select,
textarea {
  font: inherit;
}

a {
  color: inherit;
}

.surface-card {
  border: 1px solid var(--app-border);
  border-radius: 8px;
  background: var(--surface);
  box-shadow: var(--shadow-sm);
}
Created file
admin.routes.ts
+9
-0

import { Routes } from '@angular/router';

export const ADMIN_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/dashboard-page/dashboard-page').then((m) => m.DashboardPageComponent)
  }
];
Created file
metric-card.html
+10
-0

<article class="metric-card surface-card">
  <div class="metric-head">
    <span>{{ label() }}</span>
    <span class="trend" [class.is-down]="direction() === 'down'">{{ trend() }}</span>
  </div>
  <strong>{{ value() }}</strong>
  @if (detail()) {
    <p>{{ detail() }}</p>
  }
</article>
Created file
metric-card.scss
+30
-0

.metric-card {
  display: grid;
  gap: 0.75rem;
  padding: 1rem;
}

.metric-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  color: var(--muted-text);
  font-size: 0.875rem;
}

strong {
  font-size: 1.625rem;
}

p {
  margin: 0;
  color: var(--muted-text);
}

.trend {
  color: var(--success);
}

.trend.is-down {
  color: var(--danger);
}
Created file
metric-card.ts
+15
-0

import { Component, input } from '@angular/core';

@Component({
  selector: 'app-metric-card',
  standalone: true,
  templateUrl: './metric-card.html',
  styleUrl: './metric-card.scss'
})
export class MetricCardComponent {
  readonly label = input.required<string>();
  readonly value = input.required<string>();
  readonly detail = input('');
  readonly trend = input('');
  readonly direction = input<'up' | 'down'>('up');
}
Created file
occupancy-summary.html
+11
-0

<section class="surface-card summary-card">
  <h2>Resumen operativo</h2>
  <div class="summary-grid">
    @for (item of items(); track item.label) {
      <article>
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    }
  </div>
</section>
Created file
occupancy-summary.scss
+33
-0

.summary-card {
  padding: 1rem;
}

h2 {
  margin: 0 0 1rem;
  font-size: 1rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
}

article {
  display: grid;
  gap: 0.375rem;
  padding: 0.875rem;
  border-radius: 8px;
  background: var(--surface-soft);
}

span {
  color: var(--muted-text);
  font-size: 0.875rem;
}

@media (max-width: 840px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
Created file
occupancy-summary.ts
+11
-0

import { Component, input } from '@angular/core';

@Component({
  selector: 'app-occupancy-summary',
  standalone: true,
  templateUrl: './occupancy-summary.html',
  styleUrl: './occupancy-summary.scss'
})
export class OccupancySummaryComponent {
  readonly items = input<Array<{ label: string; value: string }>>([]);
}
Created file
recent-reservations.html
+29
-0

<section class="surface-card latest-card">
  <div class="card-head">
    <div>
      <h2>Ultima ejecucion</h2>
      <p>Estado mas reciente reportado por el backend.</p>
    </div>
    @if (execution()) {
      <app-status-badge
        [tone]="execution()!.status === 'success' ? 'success' : 'warning'"
        [label]="execution()!.status"
      />
    }
  </div>

  @if (execution(); as latest) {
    <dl>
      <div>
        <dt>Execution ID</dt>
        <dd>{{ latest.executionId }}</dd>
      </div>
      <div>
        <dt>Fecha</dt>
        <dd>{{ formatDate(latest.executedAt) }}</dd>
      </div>
    </dl>
  } @else {
    <p class="empty-copy">No hay ejecuciones registradas todavia.</p>
  }
</section>
Created file
recent-reservations.scss
+37
-0

.latest-card {
  padding: 1rem;
}

.card-head {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 1rem;
}

h2,
p,
dd,
dt {
  margin: 0;
}

p,
dt {
  color: var(--muted-text);
}

dl {
  display: grid;
  gap: 0.75rem;
  margin-top: 1rem;
}

div {
  display: grid;
  gap: 0.25rem;
}

.empty-copy {
  margin-top: 1rem;
}
Created file
recent-reservations.ts
+23
-0

import { Component, input } from '@angular/core';

import { formatDateTime } from '../../../../shared/utils/date-format.util';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';

@Component({
  selector: 'app-recent-reservations',
  standalone: true,
  imports: [StatusBadgeComponent],
  templateUrl: './recent-reservations.html',
  styleUrl: './recent-reservations.scss'
})
export class RecentReservationsComponent {
  readonly execution = input<{
    executionId: string;
    status: string;
    executedAt: string;
  } | null>(null);

  formatDate(value: string) {
    return formatDateTime(value);
  }
}
Created file
dashboard.mapper.ts
+46
-0

import { formatCurrency } from '../../../shared/utils/currency-format.util';
import type { DashboardApiResponseDto } from '../models/dashboard.dto';
import type { DashboardViewModel } from '../models/dashboard.model';

export function mapDashboardResponse(dto: DashboardApiResponseDto): DashboardViewModel {
  const counts = Object.entries(dto.counts).map(([label, value]) => ({
    label,
    value
  }));

  return {
    kpis: dto.overview.kpis.map((kpi) => ({
      label: kpi.label,
      value: kpi.value,
      detail: kpi.detail,
      trend: kpi.trend,
      direction: kpi.direction
    })),
    latestExecution: dto.overview.latest_execution
      ? {
          executionId: dto.overview.latest_execution.execution_id || 'Sin ejecucion',
          status: dto.overview.latest_execution.status || 'unknown',
          executedAt: dto.overview.latest_execution.executed_at || 'N/D'
        }
      : null,
    collectionCounts: counts,
    qualitySummary: [
      { label: 'Total registros', value: String(dto.quality.total_records) },
      { label: 'Aceptados', value: String(dto.quality.accepted_records) },
      { label: 'Rechazados', value: String(dto.quality.rejected_records) },
      {
        label: 'Completitud',
        value: `${Math.round((dto.quality.completeness_score || 0) * 100)}%`
      }
    ],
    occupancySummary: [
      { label: 'Eventos', value: String(dto.overview.headline.total_events) },
      { label: 'Reservas', value: String(dto.overview.headline.bookings) },
      { label: 'Conversion', value: `${dto.overview.headline.booking_rate}%` },
      {
        label: 'Precio medio',
        value: formatCurrency(dto.overview.headline.avg_price || 0)
      }
    ]
  };
}
Created file
dashboard.dto.ts
+42
-0

export interface DashboardApiResponseDto {
  counts: Record<string, number>;
  quality: {
    total_records: number;
    accepted_records: number;
    rejected_records: number;
    completeness_score: number;
  };
  overview: DashboardOverviewDto;
}

export interface DashboardOverviewDto {
  headline: {
    total_events: number;
    bookings: number;
    booking_rate: number;
    promotions: number;
    promotion_rate: number;
    avg_price: number;
    gross_revenue: number;
    distinct_hotels: number;
    distinct_destinations: number;
    distinct_countries: number;
    rejected_records: number;
    completion_rate: number;
  };
  kpis: DashboardKpiDto[];
  latest_execution: {
    execution_id?: string;
    status?: string;
    executed_at?: string;
  } | null;
}

export interface DashboardKpiDto {
  label: string;
  value: string;
  detail: string;
  trend: string;
  direction: 'up' | 'down';
  icon: string;
}
Created file
dashboard.model.ts
+19
-0

export interface DashboardViewModel {
  kpis: DashboardKpi[];
  latestExecution: {
    executionId: string;
    status: string;
    executedAt: string;
  } | null;
  collectionCounts: Array<{ label: string; value: number }>;
  qualitySummary: Array<{ label: string; value: string }>;
  occupancySummary: Array<{ label: string; value: string }>;
}

export interface DashboardKpi {
  label: string;
  value: string;
  detail: string;
  trend: string;
  direction: 'up' | 'down';
}
Created file
dashboard-page.html
+67
-0

<div class="dashboard-page">
  <app-page-header
    eyebrow="Vision ejecutiva"
    title="HotelData Dashboard"
    description="Primera migracion Angular del panel administrativo, conectada a FastAPI mediante un endpoint JSON dedicado."
  />

  @switch (viewState()) {
    @case ('loading') {
      <app-loading-state label="Cargando dashboard operativo..." />
    }
    @case ('error') {
      <app-error-state />
    }
    @case ('empty') {
      <app-empty-state
        title="No hay metricas disponibles"
        description="El dashboard no devolvio indicadores para mostrar en esta vista."
      />
    }
    @default {
      @if (viewModel(); as vm) {
        <app-occupancy-summary [items]="vm.occupancySummary" />

        <section class="kpi-grid">
          @for (kpi of vm.kpis; track kpi.label) {
            <app-metric-card
              [label]="kpi.label"
              [value]="kpi.value"
              [detail]="kpi.detail"
              [trend]="kpi.trend"
              [direction]="kpi.direction"
            />
          }
        </section>

        <section class="content-grid">
          <section class="surface-card list-card">
            <h2>Colecciones activas</h2>
            <ul>
              @for (item of vm.collectionCounts; track item.label) {
                <li>
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </li>
              }
            </ul>
          </section>

          <section class="surface-card list-card">
            <h2>Calidad de datos</h2>
            <ul>
              @for (item of vm.qualitySummary; track item.label) {
                <li>
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </li>
              }
            </ul>
          </section>
        </section>

        <app-recent-reservations [execution]="vm.latestExecution" />
      }
    }
  }
</div>
Created file
dashboard-page.scss
+57
-0

.dashboard-page {
  display: grid;
  gap: 1.5rem;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
}

.content-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.list-card {
  padding: 1rem;
}

h2 {
  margin: 0 0 1rem;
  font-size: 1rem;
}

ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.75rem;
}

li {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

span {
  color: var(--muted-text);
}

@media (max-width: 1080px) {
  .kpi-grid,
  .content-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .kpi-grid,
  .content-grid {
    grid-template-columns: 1fr;
  }
}
Created file
dashboard-page.ts
+58
-0

import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { DashboardApiService } from '../../services/dashboard-api.service';
import type { DashboardViewModel } from '../../models/dashboard.model';
import { MetricCardComponent } from '../../components/metric-card/metric-card';
import { OccupancySummaryComponent } from '../../components/occupancy-summary/occupancy-summary';
import { RecentReservationsComponent } from '../../components/recent-reservations/recent-reservations';
import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { ErrorStateComponent } from '../../../../shared/ui/error-state/error-state';
import { LoadingStateComponent } from '../../../../shared/ui/loading-state/loading-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import type { ViewState } from '../../../../shared/types/ui-state.type';

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [
    EmptyStateComponent,
    ErrorStateComponent,
    LoadingStateComponent,
    MetricCardComponent,
    OccupancySummaryComponent,
    PageHeaderComponent,
    RecentReservationsComponent
  ],
  templateUrl: './dashboard-page.html',
  styleUrl: './dashboard-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class DashboardPageComponent {
  private readonly dashboardApi = inject(DashboardApiService);
  private readonly destroyRef = inject(DestroyRef);

  readonly viewState = signal<ViewState>('loading');
  readonly viewModel = signal<DashboardViewModel | null>(null);

  constructor() {
    this.loadDashboard();
  }

  private loadDashboard() {
    this.viewState.set('loading');

    this.dashboardApi
      .getOverview()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (viewModel) => {
          this.viewModel.set(viewModel);
          this.viewState.set(viewModel.kpis.length ? 'success' : 'empty');
        },
        error: () => {
          this.viewState.set('error');
        }
      });
  }
}
Created file
dashboard-api.service.ts
+23
-0

import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map } from 'rxjs';

import { API_CONFIG } from '../../../core/api/api.config';
import { mapDashboardResponse } from '../mappers/dashboard.mapper';
import type { DashboardApiResponseDto } from '../models/dashboard.dto';

@Injectable({
  providedIn: 'root'
})
export class DashboardApiService {
  private readonly http = inject(HttpClient);
  private readonly apiConfig = inject(API_CONFIG);

  getOverview() {
    return this.http
      .get<DashboardApiResponseDto>(`${this.apiConfig.baseUrl}/dashboard/overview`, {
        withCredentials: true
      })
      .pipe(map((dto) => mapDashboardResponse(dto)));
  }
}
Created file
availability.routes.ts
+14
-0

import { Routes } from '@angular/router';

import { PlaceholderFeaturePageComponent } from '../shared-placeholder/placeholder-feature-page.component';

export const AVAILABILITY_ROUTES: Routes = [
  {
    path: '',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Availability',
      description: 'La edicion de disponibilidad e inventario requiere revisar primero los endpoints de partner.'
    }
  }
];
Created file
hotel-detail.routes.ts
+14
-0

import { Routes } from '@angular/router';

import { PlaceholderFeaturePageComponent } from '../shared-placeholder/placeholder-feature-page.component';

export const HOTEL_DETAIL_ROUTES: Routes = [
  {
    path: ':hotelId',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Detalle de hotel',
      description: 'La estructura del detalle ya esta reservada para la siguiente fase de migracion.'
    }
  }
];
Created file
filter-sidebar.html
+4
-0

<aside class="surface-card filter-sidebar">
  <h2>Filtros</h2>
  <p>La migracion del formulario de busqueda se conectara cuando exista el endpoint JSON del buscador.</p>
</aside>
Created file
filter-sidebar.scss
+14
-0

.filter-sidebar {
  padding: 1rem;
}

h2,
p {
  margin: 0;
}

p {
  margin-top: 0.5rem;
  color: var(--muted-text);
  line-height: 1.6;
}
Created file
filter-sidebar.ts
+9
-0

import { Component } from '@angular/core';

@Component({
  selector: 'app-filter-sidebar',
  standalone: true,
  templateUrl: './filter-sidebar.html',
  styleUrl: './filter-sidebar.scss'
})
export class FilterSidebarComponent {}
Created file
hotel-card.html
+23
-0

<article class="hotel-card surface-card">
  <div class="card-head">
    <div>
      <p class="eyebrow">Propiedad {{ hotel().id }}</p>
      <h2>{{ hotel().name }}</h2>
      <p>{{ hotel().location }} · Review {{ hotel().reviewLabel }}</p>
    </div>
    @if (hotel().hasPromotion) {
      <app-status-badge tone="success" label="Con promocion" />
    }
  </div>

  <dl>
    <div>
      <dt>Precio promedio</dt>
      <dd>${{ hotel().avgPriceLabel }}</dd>
    </div>
    <div>
      <dt>Conversion</dt>
      <dd>{{ hotel().conversionRate }}%</dd>
    </div>
  </dl>
</article>
Created file
hotel-card.scss
+30
-0

.hotel-card {
  padding: 1rem;
}

.card-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.eyebrow,
p,
h2,
dt,
dd {
  margin: 0;
}

.eyebrow,
p,
dt {
  color: var(--muted-text);
}

dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  margin-top: 1rem;
}
Created file
hotel-card.ts
+15
-0

import { Component, input } from '@angular/core';

import type { HotelSearchResult } from '../../models/hotel-search.model';
import { StatusBadgeComponent } from '../../../../shared/ui/status-badge/status-badge';

@Component({
  selector: 'app-hotel-card',
  standalone: true,
  imports: [StatusBadgeComponent],
  templateUrl: './hotel-card.html',
  styleUrl: './hotel-card.scss'
})
export class HotelCardComponent {
  readonly hotel = input.required<HotelSearchResult>();
}
Created file
mobile-filter-drawer.ts
+9
-0

import { Component } from '@angular/core';

@Component({
  selector: 'app-mobile-filter-drawer',
  standalone: true,
  template: '',
  styles: ''
})
export class MobileFilterDrawerComponent {}
Created file
sort-control.ts
+9
-0

import { Component } from '@angular/core';

@Component({
  selector: 'app-sort-control',
  standalone: true,
  template: '<div class="sort-control">Ordenacion disponible en la siguiente fase de migracion.</div>',
  styles: '.sort-control { color: var(--muted-text); font-size: 0.875rem; }'
})
export class SortControlComponent {}
Created file
hotel-search.routes.ts
+9
-0

import { Routes } from '@angular/router';

export const HOTEL_SEARCH_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () =>
      import('./pages/hotel-search-page/hotel-search-page').then((m) => m.HotelSearchPageComponent)
  }
];
Created file
hotel-search.mapper.ts
+18
-0

import type { HotelSearchDto } from '../models/hotel-search.dto';
import type { HotelSearchResult } from '../models/hotel-search.model';

export function mapHotelSearchItems(dto: HotelSearchDto): HotelSearchResult[] {
  return dto.items.map((item) => ({
    id: item.prop_id,
    name: item.hotel_label,
    location: item.country_display_name,
    stars: item.prop_starrating,
    reviewLabel: item.review_label,
    hasPromotion: item.has_promotion,
    avgPriceLabel: item.avg_price_label,
    reservations: item.reservations,
    clicks: item.clicks,
    conversionRate: item.conversion_rate,
    destinationLabels: item.destination_labels
  }));
}
Created file
hotel-search.dto.ts
+15
-0

export interface HotelSearchDto {
  items: Array<{
    prop_id: number;
    hotel_label: string;
    country_display_name: string;
    prop_starrating: number | null;
    review_label: string;
    has_promotion: boolean;
    avg_price_label: string;
    reservations: number;
    clicks: number;
    conversion_rate: number;
    destination_labels: string[];
  }>;
}
Created file
hotel-search.model.ts
+13
-0

export interface HotelSearchResult {
  id: number;
  name: string;
  location: string;
  stars: number | null;
  reviewLabel: string;
  hasPromotion: boolean;
  avgPriceLabel: string;
  reservations: number;
  clicks: number;
  conversionRate: number;
  destinationLabels: string[];
}
Created file
hotel-search-page.html
+18
-0

<div class="hotel-search-page">
  <app-page-header
    eyebrow="Cliente / viajero"
    title="Buscar hoteles"
    description="Estructura inicial del flujo traveler. La migracion completa del buscador dependera de un endpoint JSON dedicado."
  />

  <div class="page-grid">
    <app-filter-sidebar />
    <section class="results-column">
      <app-sort-control />
      <app-empty-state
        title="Migracion del buscador en progreso"
        description="La vista Angular ya tiene el espacio y las responsabilidades separadas para filtros, resultados y ordenacion."
      />
    </section>
  </div>
</div>
Created file
hotel-search-page.scss
+21
-0

.hotel-search-page {
  display: grid;
  gap: 1.5rem;
}

.page-grid {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 1rem;
}

.results-column {
  display: grid;
  gap: 1rem;
}

@media (max-width: 920px) {
  .page-grid {
    grid-template-columns: 1fr;
  }
}
Created file
hotel-search-page.ts
+15
-0

import { Component } from '@angular/core';

import { EmptyStateComponent } from '../../../../shared/ui/empty-state/empty-state';
import { PageHeaderComponent } from '../../../../shared/ui/page-header/page-header';
import { FilterSidebarComponent } from '../../components/filter-sidebar/filter-sidebar';
import { SortControlComponent } from '../../components/sort-control/sort-control';

@Component({
  selector: 'app-hotel-search-page',
  standalone: true,
  imports: [EmptyStateComponent, FilterSidebarComponent, PageHeaderComponent, SortControlComponent],
  templateUrl: './hotel-search-page.html',
  styleUrl: './hotel-search-page.scss'
})
export class HotelSearchPageComponent {}
Created file
hotel-search-api.service.ts
+11
-0

import { inject, Injectable } from '@angular/core';
import { of } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class HotelSearchApiService {
  getSearchPreview() {
    return of([]);
  }
}
Created file
properties.routes.ts
+14
-0

import { Routes } from '@angular/router';

import { PlaceholderFeaturePageComponent } from '../shared-placeholder/placeholder-feature-page.component';

export const PROPERTIES_ROUTES: Routes = [
  {
    path: '',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Properties',
      description: 'El modulo administrativo de propiedades queda preparado para la siguiente ola de migracion.'
    }
  }
];
Created file
reservations.routes.ts
+14
-0

import { Routes } from '@angular/router';

import { PlaceholderFeaturePageComponent } from '../shared-placeholder/placeholder-feature-page.component';

export const RESERVATIONS_ROUTES: Routes = [
  {
    path: '',
    component: PlaceholderFeaturePageComponent,
    data: {
      title: 'Reservas',
      description: 'La migracion del modulo de reservas se hara sobre endpoints JSON dedicados.'
    }
  }
];
Created file
placeholder-feature-page.component.ts
+24
-0

import { Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

import { EmptyStateComponent } from '../../shared/ui/empty-state/empty-state';
import { PageHeaderComponent } from '../../shared/ui/page-header/page-header';

@Component({
  selector: 'app-placeholder-feature-page',
  standalone: true,
  imports: [EmptyStateComponent, PageHeaderComponent],
  template: `
    <div class="placeholder-page">
      <app-page-header [title]="title" description="Ruta preparada dentro de la nueva arquitectura Angular." />
      <app-empty-state [title]="title" [description]="description" />
    </div>
  `,
  styles: '.placeholder-page { display: grid; gap: 1.5rem; }'
})
export class PlaceholderFeaturePageComponent {
  private readonly route = inject(ActivatedRoute);

  readonly title = this.route.snapshot.data['title'] as string;
  readonly description = this.route.snapshot.data['description'] as string;
}
Created file
ui-state.type.ts
+1
-0

export type ViewState = 'idle' | 'loading' | 'success' | 'empty' | 'error';
Created file
empty-state.html
+6
-0

<section class="state-card surface-card" aria-live="polite">
  <h2>{{ title() }}</h2>
  @if (description()) {
    <p>{{ description() }}</p>
  }
</section>
Created file
empty-state.scss
+13
-0

.state-card {
  padding: 1.25rem;
}

h2,
p {
  margin: 0;
}

p {
  margin-top: 0.5rem;
  color: var(--muted-text);
}
Created file
empty-state.ts
+12
-0

import { Component, input } from '@angular/core';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  templateUrl: './empty-state.html',
  styleUrl: './empty-state.scss'
})
export class EmptyStateComponent {
  readonly title = input.required<string>();
  readonly description = input('');
}
Created file
error-state.html
+4
-0

<section class="state-card surface-card" aria-live="assertive">
  <h2>{{ title() }}</h2>
  <p>{{ description() }}</p>
</section>
Created file
error-state.scss
+14
-0

.state-card {
  padding: 1.25rem;
  border-color: rgba(201, 61, 50, 0.25);
}

h2,
p {
  margin: 0;
}

p {
  margin-top: 0.5rem;
  color: var(--muted-text);
}
Created file
error-state.ts
+12
-0

import { Component, input } from '@angular/core';

@Component({
  selector: 'app-error-state',
  standalone: true,
  templateUrl: './error-state.html',
  styleUrl: './error-state.scss'
})
export class ErrorStateComponent {
  readonly title = input('No fue posible cargar esta seccion');
  readonly description = input('Intenta nuevamente o revisa la conectividad con la API.');
}
Created file
loading-state.html
+4
-0

<section class="loading-card surface-card" aria-live="polite" aria-busy="true">
  <div class="spinner" aria-hidden="true"></div>
  <p>{{ label() }}</p>
</section>
Created file
loading-state.scss
+21
-0

.loading-card {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.25rem;
}

.spinner {
  width: 1rem;
  height: 1rem;
  border: 2px solid rgba(20, 99, 255, 0.16);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
Created file
loading-state.ts
+11
-0

import { Component, input } from '@angular/core';

@Component({
  selector: 'app-loading-state',
  standalone: true,
  templateUrl: './loading-state.html',
  styleUrl: './loading-state.scss'
})
export class LoadingStateComponent {
  readonly label = input('Cargando informacion...');
}
Created file
page-header.html
+9
-0

<header class="page-header">
  @if (eyebrow()) {
    <p class="eyebrow">{{ eyebrow() }}</p>
  }
  <h1>{{ title() }}</h1>
  @if (description()) {
    <p class="description">{{ description() }}</p>
  }
</header>
Created file
page-header.scss
+23
-0

.page-header {
  display: grid;
  gap: 0.5rem;
}

.eyebrow {
  margin: 0;
  font-size: 0.875rem;
  color: var(--accent);
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-size: clamp(1.75rem, 2.5vw, 2.5rem);
}

.description {
  margin: 0;
  max-width: 70ch;
  color: var(--muted-text);
  line-height: 1.6;
}
Created file
page-header.ts
+13
-0

import { Component, input } from '@angular/core';

@Component({
  selector: 'app-page-header',
  standalone: true,
  templateUrl: './page-header.html',
  styleUrl: './page-header.scss'
})
export class PageHeaderComponent {
  readonly eyebrow = input('');
  readonly title = input.required<string>();
  readonly description = input('');
}
Created file
status-badge.html
+1
-0

<span class="status-badge" [class]="'status-badge tone-' + tone()">{{ label() }}</span>
Created file
status-badge.scss
+29
-0

.status-badge {
  display: inline-flex;
  align-items: center;
  min-height: 2rem;
  padding: 0 0.75rem;
  border-radius: 999px;
  font-size: 0.875rem;
  font-weight: 600;
}

.tone-neutral {
  background: #eaf1fb;
  color: #3e506b;
}

.tone-success {
  background: rgba(15, 138, 96, 0.14);
  color: var(--success);
}

.tone-warning {
  background: rgba(201, 129, 5, 0.14);
  color: var(--warning);
}

.tone-danger {
  background: rgba(201, 61, 50, 0.14);
  color: var(--danger);
}
Created file
status-badge.ts
+12
-0

import { Component, input } from '@angular/core';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  templateUrl: './status-badge.html',
  styleUrl: './status-badge.scss'
})
export class StatusBadgeComponent {
  readonly tone = input<'neutral' | 'success' | 'warning' | 'danger'>('neutral');
  readonly label = input.required<string>();
}
Created file
currency-format.util.ts
+11
-0

export function formatCurrency(
  value: number,
  currency = 'USD',
  locale = 'es-EC'
): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    maximumFractionDigits: 2
  }).format(value);
}
Created file
date-format.util.ts
+15
-0

export function formatDateTime(value: string | null | undefined, locale = 'es-EC'): string {
  if (!value) {
    return 'N/D';
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(parsed);
}
La base ya está armada en serio. Antes de verificar compilación voy a ajustar un par de detalles de consistencia del scaffold para que no nos exploten cosas tontas del template inicial de Angular.

Edited 3 files
Ya está el grueso del scaffold. Ahora corro build de Angular para detectar errores reales de compilación y limpiar los últimos bordes antes de seguir migrando pantallas.

Quedó compilando bien. Voy a sacar un estado final del repo para resumirte exactamente qué migré y desde dónde conviene continuar mañana sin volver a leer todo de cero.

Sí, me guié por AGENTS.md y por las skills de angular-senior, frontend-engineering y jinja-to-angular-migration, leyéndolas al vuelo en vez de “guardar todo” en contexto. Ya dejé arrancada la migración con estructura por responsabilidad y una primera pantalla migrada de verdad.

Lo que hice:

Organicé frontend/src/app en core, shared y features, con shells público/admin, config API, auth base, componentes reutilizables y rutas lazy.
Migré el dashboard legacy a Angular como primera pantalla real: frontend/src/app/features/admin/pages/dashboard-page/dashboard-page.ts (line 1)
Creé el endpoint JSON para que Angular no dependa del HTML Jinja: src/app/features/dashboard/routes.py (line 1)
Añadí una base de sesión para Angular con /api/auth/me: src/app/modules/auth/routes.py (line 1)
Documenté el mapa de migración: docs/frontend-migration-map.md (line 1)
Las piezas más importantes quedaron aquí:

frontend/src/app/app.routes.ts (line 1)
frontend/src/app/core/layout/admin-shell/admin-shell.ts (line 1)
frontend/src/app/core/layout/public-shell/public-shell.ts (line 1)
frontend/src/app/core/api/api.config.ts (line 1)
frontend/src/app/features/admin/services/dashboard-api.service.ts (line 1)
frontend/src/app/features/hotel-search/hotel-search.routes.ts (line 1)
También dejé el buscador, properties, availability, reservations y hotel detail scaffolded dentro de la nueva arquitectura, pero todavía como base de migración, no como migración completa. El dashboard sí quedó enlazado a FastAPI con contrato tipado.

Verificación: corrí npm run build en frontend/ y compiló bien.

Siguiente paso natural: migrar hotel-search de forma real, creando su endpoint JSON y conectando filtros, resultados, empty/error/loading state dentro de la estructura que ya quedó lista.


frontend-migration-map.md
Document · MD
Open in

Edited 81 files
+1,604
-68
Undo
Review

hoteldata_project/docs/frontend-migration-map.md
+29
-0

hoteldata_project/frontend/angular.json
+6
-3

hoteldata_project/frontend/proxy.conf.json
+7
-0

hoteldata_project/src/app/features/dashboard/routes.py
+9
-0

hoteldata_project/src/app/main.py
+2
-0

hoteldata_project/src/app/modules/auth/routes.py
+24
-0

hoteldata_project/frontend/src/app/app.config.ts
+20
-11

hoteldata_project/frontend/src/app/app.html
+1
-0

hoteldata_project/frontend/src/app/app.routes.ts
+56
-3

hoteldata_project/frontend/src/app/app.scss
+4
-0

hoteldata_project/frontend/src/app/app.ts
+10
-12

hoteldata_project/frontend/src/app/core/api/api-error.model.ts
+6
-0

hoteldata_project/frontend/src/app/core/api/api.config.ts
+12
-0

hoteldata_project/frontend/src/app/core/api/http-error.interceptor.ts
+45
-25

hoteldata_project/frontend/src/app/core/auth/auth.guard.ts
+19
-0

hoteldata_project/frontend/src/app/core/auth/auth.models.ts
+33
-0

hoteldata_project/frontend/src/app/core/auth/auth.service.ts
+63
-0

hoteldata_project/frontend/src/app/core/layout/admin-shell/admin-shell.html
+16
-0

hoteldata_project/frontend/src/app/core/layout/admin-shell/admin-shell.scss
+54
-0

hoteldata_project/frontend/src/app/core/layout/admin-shell/admin-shell.ts
+16
-0

hoteldata_project/frontend/src/app/core/layout/public-shell/public-shell.html
+14
-0

hoteldata_project/frontend/src/app/core/layout/public-shell/public-shell.scss
+41
-0

hoteldata_project/frontend/src/app/core/layout/public-shell/public-shell.ts
+16
-0

hoteldata_project/frontend/src/styles.scss
+50
-0

hoteldata_project/frontend/src/app/features/admin/admin.routes.ts
+9
-0

hoteldata_project/frontend/src/app/features/admin/components/metric-card/metric-card.html
+10
-0

hoteldata_project/frontend/src/app/features/admin/components/metric-card/metric-card.scss
+30
-0

hoteldata_project/frontend/src/app/features/admin/components/metric-card/metric-card.ts
+15
-0

hoteldata_project/frontend/src/app/features/admin/components/occupancy-summary/occupancy-summary.html
+11
-0

hoteldata_project/frontend/src/app/features/admin/components/occupancy-summary/occupancy-summary.scss
+33
-0

hoteldata_project/frontend/src/app/features/admin/components/occupancy-summary/occupancy-summary.ts
+11
-0

hoteldata_project/frontend/src/app/features/admin/components/recent-reservations/recent-reservations.html
+29
-0

hoteldata_project/frontend/src/app/features/admin/components/recent-reservations/recent-reservations.scss
+37
-0

hoteldata_project/frontend/src/app/features/admin/components/recent-reservations/recent-reservations.ts
+23
-0

hoteldata_project/frontend/src/app/features/admin/mappers/dashboard.mapper.ts
+46
-0

hoteldata_project/frontend/src/app/features/admin/models/dashboard.dto.ts
+42
-0

hoteldata_project/frontend/src/app/features/admin/models/dashboard.model.ts
+19
-0

hoteldata_project/frontend/src/app/features/admin/pages/dashboard-page/dashboard-page.html
+67
-0

hoteldata_project/frontend/src/app/features/admin/pages/dashboard-page/dashboard-page.scss
+57
-0

hoteldata_project/frontend/src/app/features/admin/pages/dashboard-page/dashboard-page.ts
+58
-0

hoteldata_project/frontend/src/app/features/admin/services/dashboard-api.service.ts
+23
-0

hoteldata_project/frontend/src/app/features/availability/availability.routes.ts
+14
-0

hoteldata_project/frontend/src/app/features/hotel-detail/hotel-detail.routes.ts
+14
-0

hoteldata_project/frontend/src/app/features/hotel-search/components/filter-sidebar/filter-sidebar.html
+4
-0

hoteldata_project/frontend/src/app/features/hotel-search/components/filter-sidebar/filter-sidebar.scss
+14
-0

hoteldata_project/frontend/src/app/features/hotel-search/components/filter-sidebar/filter-sidebar.ts
+9
-0

hoteldata_project/frontend/src/app/features/hotel-search/components/hotel-card/hotel-card.html
+23
-0

hoteldata_project/frontend/src/app/features/hotel-search/components/hotel-card/hotel-card.scss
+30
-0

hoteldata_project/frontend/src/app/features/hotel-search/components/hotel-card/hotel-card.ts
+15
-0

hoteldata_project/frontend/src/app/features/hotel-search/components/mobile-filter-drawer/mobile-filter-drawer.ts
+10
-1

hoteldata_project/frontend/src/app/features/hotel-search/components/sort-control/sort-control.ts
+9
-0

hoteldata_project/frontend/src/app/features/hotel-search/hotel-search.routes.ts
+9
-0

hoteldata_project/frontend/src/app/features/hotel-search/mappers/hotel-search.mapper.ts
+18
-0

hoteldata_project/frontend/src/app/features/hotel-search/models/hotel-search.dto.ts
+15
-0

hoteldata_project/frontend/src/app/features/hotel-search/models/hotel-search.model.ts
+13
-0

hoteldata_project/frontend/src/app/features/hotel-search/pages/hotel-search-page/hotel-search-page.html
+18
-0

hoteldata_project/frontend/src/app/features/hotel-search/pages/hotel-search-page/hotel-search-page.scss
+21
-0

hoteldata_project/frontend/src/app/features/hotel-search/pages/hotel-search-page/hotel-search-page.ts
+15
-0

hoteldata_project/frontend/src/app/features/hotel-search/services/hotel-search-api.service.ts
+11
-0

hoteldata_project/frontend/src/app/features/properties/properties.routes.ts
+14
-0

hoteldata_project/frontend/src/app/features/reservations/reservations.routes.ts
+14
-0

hoteldata_project/frontend/src/app/features/shared-placeholder/placeholder-feature-page.component.ts
+24
-0

hoteldata_project/frontend/src/app/shared/types/ui-state.type.ts
+1
-0

hoteldata_project/frontend/src/app/shared/ui/empty-state/empty-state.html
+6
-0

hoteldata_project/frontend/src/app/shared/ui/empty-state/empty-state.scss
+13
-0

hoteldata_project/frontend/src/app/shared/ui/empty-state/empty-state.ts
+12
-0

hoteldata_project/frontend/src/app/shared/ui/error-state/error-state.html
+4
-0

hoteldata_project/frontend/src/app/shared/ui/error-state/error-state.scss
+14
-0

hoteldata_project/frontend/src/app/shared/ui/error-state/error-state.ts
+12
-0

hoteldata_project/frontend/src/app/shared/ui/loading-state/loading-state.html
+4
-0

hoteldata_project/frontend/src/app/shared/ui/loading-state/loading-state.scss
+21
-0

hoteldata_project/frontend/src/app/shared/ui/loading-state/loading-state.ts
+11
-0

hoteldata_project/frontend/src/app/shared/ui/page-header/page-header.html
+9
-0

hoteldata_project/frontend/src/app/shared/ui/page-header/page-header.scss
+23
-0

hoteldata_project/frontend/src/app/shared/ui/page-header/page-header.ts
+13
-0

hoteldata_project/frontend/src/app/shared/ui/status-badge/status-badge.html
+1
-0

hoteldata_project/frontend/src/app/shared/ui/status-badge/status-badge.scss
+29
-0

hoteldata_project/frontend/src/app/shared/ui/status-badge/status-badge.ts
+12
-0

hoteldata_project/frontend/src/app/shared/utils/currency-format.util.ts
+11
-0

hoteldata_project/frontend/src/app/shared/utils/date-format.util.ts
+15
-0

hoteldata_project/frontend/src/app/app.spec.ts
+6
-13

Collapse files