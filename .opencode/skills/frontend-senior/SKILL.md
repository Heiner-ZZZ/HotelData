---
name: frontend-senior
description: Use when designing, reviewing, or refactoring Angular frontend code. Covers Signals-first reactivity, zoneless change detection (default in Angular 21), lazy loading, performance budgets, component architecture, SSR/SSG, micro-frontends, state management, and testing strategies.
---

# Senior Frontend Engineer — Angular 21+

## 2026 Landscape
- **Angular 21**: Zoneless by default (`provideZonelessChangeDetection()` is now default in `ng new`)
- **Signals** are the primary reactivity primitive — RxJS is for async orchestration only
- **Standalone components** (no `NgModule`) are the only pattern — `NgModule` is legacy
- **`@angular/build`** uses Vite + esbuild — no more Webpack
- **`@angular/ssr`** (SSR/SSG) stable and recommended for SEO/content apps
- **Micro-frontends**: Native Federation / Module Federation via `@angular-architects/native-federation`
- **AI tooling**: Angular MCP Server for AI-assisted development

## Architecture Principles

### 0. UX & UI Design Principles

#### Visual Design Rules
- **0 emojis** — never use emoji characters in UI text; use Material Symbols instead
- **Icons always** — every visual indicator, status, badge, section header, nav item, CTA, and action affordance must use an icon (not text emoji)
- Use Material Symbols (Google Fonts) as the only icon system — consistent, scalable, accessible
- Icons must have `aria-hidden="true"` when decorative (no label needed), or `aria-label` when semantic
- Icon size and weight should be consistent within each context (nav: 1.15rem, hero cards: 1.75rem, form inputs: 1.35rem, buttons: 1.15rem)

#### Layout & Spacing
- Use CSS Grid for page-level layouts, Flexbox for component-level alignment
- Consistent 8px/16px grid for spacing (padding, margin, gap)
- Max content width: 1280px for admin/management pages; full-bleed for public pages
- Hero sections use a 2-column grid (text + decorative) on desktop, stack on mobile
- Forms should be single-column, max 440px wide for readability

#### Typography
- System font stack: `Inter, "Segoe UI", Arial, sans-serif`
- Hierarchy: eyebrow (0.78rem, uppercase, accent color) → title (1.05rem-2rem) → body (0.9rem-1rem) → muted/caption (0.78-0.82rem)
- Line height: headings 1.08-1.1, body 1.6-1.7
- Font weight: regular 400, medium 500, semi-bold 600, bold 700

#### Color
- Use CSS custom properties from `styles.scss` (`--accent`, `--success`, `--warning`, `--danger`, `--muted-text`, `--app-border`, etc.)
- Surface cards: white with subtle border + shadow (`var(--shadow-sm)`)
- Interactive states: hover uses `rgba(20, 99, 255, 0.04-0.08)`, active uses `rgba(20, 99, 255, 0.12)`
- Error states: red background `#fff2f1` + border `#f5c8c3` + text `#a13022`
- Always use `var(--muted-text)` for secondary/helper text

#### Component Patterns
- **Surface card**: `border: 1px solid var(--app-border)`, `border-radius: 8px`, `background: var(--surface)`, `box-shadow: var(--shadow-sm)`
- **Hero card**: centered grid layout with icon + label + value + description
- **Accordion**: collapsible sections, one open at a time, all closed by default
- **Status badge**: pill-shaped with tone classes (`success`, `warning`, `danger`)
- **Buttons**: pill or rounded-rect, accent background, white text, disabled state at 0.78 opacity
- **Tables**: `table-wrap` for horizontal scroll on mobile, sticky header, alternating row bg, bordered
- **Loading state**: centered spinner/placeholder with descriptive label
- **Empty state**: centered message with title + description + optional CTA
- **Error state**: red-toned card with title, description, optional retry CTA

#### Accessibility
- All interactive elements must be focusable and have visible focus rings (`box-shadow` on `:focus`)
- `aria-label` on icon-only buttons and SVG controls
- `aria-hidden="true"` on decorative icons
- `aria-pressed` on toggle buttons
- `aria-expanded` on accordion triggers and dropdown menus
- Color contrast ratio ≥ 4.5:1 for text, ≥ 3:1 for large text and UI components
- `sr-only` utility class for screen-reader-only text
- Form fields must have associated `<label>` elements (not placeholders as labels)
- Error messages must be visible text, not just color changes

#### Login Page Specific
- Full-viewport layout: hero (copy + branding) on left, form card on right; stacks on mobile
- Brand logo is the primary visual — no redundant text next to it
- Form inputs have leading icon (person for username, lock for password)
- Password visibility toggle with eye icon (SVG inline), not text
- Submit button shows icon (login/arrow) + label; shows spinner icon while submitting
- Footnote with shield icon for security reassurance
- Error banner with red background, positioned above form
- Kicker text (eyebrow) above brand for context ("Control de acceso")

### 1. Signal-First Reactivity (2026 Standard)
```typescript
// ✅ Correct: Signals for UI state
readonly count = signal(0);
readonly doubled = computed(() => this.count() * 2);

// ✅ Correct: RxJS for async streams, convert at UI boundary
private readonly search$ = new Subject<string>();
readonly results = toSignal(this.search$.pipe(
  debounceTime(300),
  switchMap(term => this.api.search(term))
));

// ❌ Wrong: RxJS for local UI state
private readonly count$ = new BehaviorSubject(0);
readonly count = this.count$.asObservable();
```

#### New in Angular 21:
- `linkedSignal()` — derived state that can be written to
- `resource()` — async data fetching with Signals (replaces `async` pipe patterns)
- `effect()` — use sparingly, only for side effects (console, localStorage, analytics)

### 2. Zoneless Change Detection
Enable in existing project:
```typescript
provideExperimentalZonelessChangeDetection()
```
In Angular 21+ new projects it's on by default. Benefits:
- Smaller bundle (no `zone.js`)
- Clearer stack traces
- Predictable rendering — only signal-dependent bindings update
- 25–40% fewer change detection cycles in dashboards

### 3. Component Architecture
```
Standalone Components (always — no NgModule):

Smart (container)       Dumb (presentational)
───────────────────     ───────────────────────
Uses inject()           Receives input()
Manages state           Emits output()
Handles async           No DI except pipes
Calls services          Pure templates
```

```typescript
@Component({
  selector: 'app-user-card',
  standalone: true,
  imports: [DatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `...`
})
export class UserCardComponent {
  readonly user = input.required<User>();
  readonly dismissed = output<void>();
}
```

### 4. Performance Budgets
| Metric | Budget |
|---|---|
| Initial bundle (gzip) | < 80 kB |
| Lazy chunk (gzip) | < 30 kB |
| First Contentful Paint | < 1.5s |
| Time to Interactive | < 2.5s |
| Lighthouse score | > 90 |

#### Techniques:
- `@defer` blocks for heavy non-critical content (images, charts, maps)
- Virtual scroll via `@angular/cdk/scrolling` for lists > 200 items
- `track` in `@for` — always provide a unique key
- Preload critical lazy chunks with `<link rel="modulepreload">`
- `image` directive (`NgOptimizedImage`) with `priority` for LCP

### 5. Folder Structure (Current Project)
```
src/app/
  core/              # Singletons (auth, api, guards, interceptors)
    auth/            # AuthService, auth.guard, auth.interceptor
    api/             # ApiConfig, HttpErrorInterceptor
    layout/          # Shell components (public, account, management, system-admin)
  features/          # Lazy-loaded feature modules
    hotel-search/    # feature with own routes.ts
    hotel-detail/
    reservations/
    management/
    account/
    system-admin/
  shared/            # Reusable UI (buttons, modals, pipes, directives)
    ui/              # Standalone UI components
```

### 6. Routing & Lazy Loading
```typescript
// app.routes.ts — every feature is lazy
{
  path: 'search',
  loadChildren: () => import('./features/hotel-search/hotel-search.routes')
    .then(m => m.HOTEL_SEARCH_ROUTES)
}
```
- Preload strategy: `withPreloading(PreloadAllModules)` or custom for critical features
- Route guards: `canActivate: [authGuard, roleGuard]` with `data: { allowedRoles: [...] }`

### 7. State Management Decision Tree
| Scenario | Solution |
|---|---|
| Local component state | `signal()` |
| Derived state | `computed()` |
| Server state (GET) | `resource()` or `HttpClient` + `toSignal()` |
| Server state (mutate) | `HttpClient` + `signal` + manual update |
| Cross-component shared | Service with `signal()` (providedIn: 'root') |
| Complex global state | NgRx Signals (new) or plain service |
| Form state | `@angular/forms` with `ReactiveFormsModule` |

### 8. HTTP & Interceptors
```typescript
provideHttpClient(
  withInterceptors([
    authInterceptor,         // withCredentials
    httpErrorInterceptor,    // global error handling
    loggingInterceptor,      // request/response logging
  ])
)
```
- Use `withCredentials: true` for cookie-based auth
- Never store tokens client-side — use `httpOnly` cookies (already done in this project)

### 9. Forms
- `ReactiveFormsModule` with `nonNullable` form controls
- Typed forms: `FormGroup<{ email: FormControl<string> }>`
- Async validators for remote checks (email uniqueness)
- `form.valid` + `form.markAllAsTouched()` pattern

### 10. Testing (2026 Practices)
- **Vitest** (faster than Jest for Angular) — or Karma with `@angular-builders/jest`
- `TestBed` with `provideExperimentalZonelessChangeDetection` for zoneless tests
- CDK Test Harnesses over raw `querySelector`
- `HarnessLoader` for Material/CDK component testing
- Signal testing: read `.()` value directly, no subscribe needed
- Component tests: `await fixture.whenStable()` after signal changes

### 11. Security Checklist
- [ ] `DomSanitizer` bypassed only when absolutely necessary
- [ ] All user content sanitized via Angular's built-in sanitization
- [ ] `withCredentials` on every API call
- [ ] Route guards on all protected routes
- [ ] Interceptor handles 401 → redirect to login
- [ ] No secrets in frontend code or environment files
- [ ] CSP headers configured in nginx

### 12. Build & Deploy (This Project)
- **Build**: `@angular/build:application` → outputs `dist/frontend/browser/`
- **Serve**: Multi-stage Docker (node:22-alpine build → nginx:alpine)
- **Nginx proxy**: `/api/` → `app:8000/api/`, `/auth/` → `app:8000/auth/`
- **Dev**: `ng serve --proxy-config proxy.conf.json`

### References
- Angular 21 changelog: https://github.com/angular/angular/blob/main/CHANGELOG.md
- Signals guide: https://angular.io/guide/signals
- Zoneless: https://angular.io/guide/zoneless
- Performance: https://angular.io/guide/performance
