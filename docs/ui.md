# UI Guidelines

## Goal

- Build mobile-first interfaces for FAN FAN.
- Prefer clarity, reuse, and safe defaults over novelty.
- Keep decisions easy to repeat across screens.
- Keep this document focused on FAN FAN-specific UI conventions.

## Required UI Skills

- Use `svelte-code-writer` and `svelte-core-bestpractices` for Svelte components and Svelte UI refactors.
- Use `tailwind-css-patterns` when working with Tailwind CSS (project uses v4; config lives in `app.css`).

## Reuse Existing Patterns

- Reuse `frontend/src/lib/components/SectionHeader.svelte` for page titles and short descriptions.
- Reuse shared toast feedback through `frontend/src/lib/components/ToastContainer.svelte` and `frontend/src/lib/stores/toasts.svelte`.
- Reuse page shell spacing from `frontend/src/routes/(app)/+layout.svelte` and `frontend/src/routes/(auth)/+layout.svelte`.
- Reuse existing card, form, modal, and list patterns from `frontend/src/lib/components/` before adding a new variant.
- Match established large mobile action sizing before inventing a new button pattern.
- Do not introduce a new visual pattern when an established equivalent already exists.

## Component Selection

- Prefer official Flowbite-Svelte components before custom UI.
- Check existing project components before creating a new component.
- Use `flowbite-svelte-icons` for icons.
- Add icons only when they improve recognition or scanning.
- Do not build custom controls when Flowbite-Svelte already covers the need.

## Language and Copy

- Write all user-facing text in Russian.
- Keep labels, buttons, placeholders, helper text, alerts, empty states, and toasts in Russian.
- Keep copy short, direct, and action-oriented.
- Explain what the user can do next when a state blocks progress.
- Replace English placeholder examples unless an external format requires Latin text.
- Do not show raw backend messages or internal technical wording.

## Layout

- Design for a narrow mobile viewport first.
- Start with a single-column layout unless wider screens clearly improve the task.
- Use flex, grid, and gap-based spacing.
- Keep content inside the established page containers.
- Add bottom spacing when fixed mobile navigation is present.
- Keep primary actions reachable on mobile.
- Avoid arbitrary fixed heights, widths, and spacing unless an external constraint requires them.

## Forms and Feedback

- Keep forms easy to scan in a single mobile column.
- Use inline helper or error text near the relevant field.
- Add a password visibility toggle for password inputs.
- Disable repeat submission while a request is in flight.
- Show a spinner or progress label during async submission.
- Use toasts for final action results, not for field-level validation.
- Provide loading, empty, success, and error states when the user can encounter them.
- Use inline alerts or helper text for persistent context and recoverable form issues.
- Make empty states explain why the area is empty and what the user can do next.
- Keep success and error wording consistent across screens.

## Review Checklist

- Existing project patterns were reused before new UI was added.
- Flowbite-Svelte components were used where they fit.
- All user-facing copy, including placeholders and helper text, is in Russian.
- Mobile layout works before desktop refinements.
- Fixed mobile navigation does not cover content or primary actions.
- Loading, empty, success, and error states are present when needed.
- Field validation appears near the field, and transient outcomes use toasts.
- Relevant UI skills were used for implementation or review.
