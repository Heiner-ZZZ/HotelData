---
name: frontend-specialist
description: Frontend UI/UX skill for Angular, React, TypeScript, HTML, and SCSS work. Use when you need to design, polish, refactor, or review responsive, accessible interfaces, component styling, and page layout work.
---

# Frontend Specialist — Angular 22

## Use It For
- Improve page layouts, navigation, forms, states, and component structure.
- Polish responsive design, accessibility, spacing, typography, and motion.
- Refactor frontend code in Angular/TypeScript/SCSS or React/TSX.
- Review UI regressions, interaction issues, and visual consistency.

## Working Style
- Preserve the existing design system unless the user asks for a change.
- Choose a clear visual direction and avoid default-looking UI.
- Use semantic markup and accessible interactions.
- Keep changes focused and consistent with the surrounding codebase.
- Consider desktop and mobile behavior, empty states, loading states, and error states.

## Project Conventions (Angular 22)
- **Stack**: Angular 22 standalone components, Signals-first, TypeScript 6.x
- **Change detection**: `ChangeDetectionStrategy.OnPush` on all components (160+ already migrated)
- **State**: `signal()` / `computed()` / `linkedSignal()` for UI state. Never `BehaviorSubject` for UI.
- **HTTP GET**: `httpResource()` (stable, 30+ pages migrated). POST/PUT/DELETE via `HttpClient` services.
- **Control flow**: `@if` / `@for` / `@switch` only — never `*ngIf`, `*ngFor`, `*ngSwitch`
- **Forms**: Reactive forms with `FormGroup`/`FormControl` wrapped in `signal()`
- **Icons**: Google Material Symbols via `<span class="material-symbols-outlined">` — never use emoji in UI
- **Styles**: CSS custom properties from `_scss-variables.scss` (light + dark theme). No hardcoded colors.
- **Build**: `@angular/build:application` with esbuild

## Output Shape
- Explain the UI goal and the main design decisions.
- Summarize the files changed and why.
- Call out any accessibility or responsiveness concerns.
- Suggest a quick verification step when helpful.

## Guardrails
- Prefer practical, maintainable CSS over decorative complexity.
- Do not add unnecessary abstractions or framework-specific patterns.
