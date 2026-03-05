# UI Guidelines

## Goal

Produce interfaces that are clear on mobile, consistent with Flowbite-Svelte, and safe for real users.

## Component Selection

- Prefer official Flowbite-Svelte components before creating custom UI.
- Check component capabilities before building a custom alternative.
- Use icons from `flowbite-svelte-icons` and verify the icon name from documentation.

## Language and Copy

- All labels, buttons, placeholders, empty states, errors, and helper text must be in Russian.
- Keep copy concise, direct, and user-oriented.
- Avoid raw technical wording in user-facing text.

## Layout

- Design for mobile first.
- Add larger breakpoint behavior only when the layout clearly benefits from it.
- Use simple layout primitives such as flex, grid, and gap-based spacing.
- Avoid arbitrary fixed spacing and sizing unless a hard external constraint requires it.
- Keep interactive elements away from screen edges and fixed navigation overlap zones.

## Cards and Surfaces

- Ensure cards have clear internal padding.
- Keep surface hierarchy obvious through spacing, contrast, and typography.
- Do not let content touch card edges.

## Forms

- Inputs should be easy to scan, easy to tap, and clearly labeled.
- Use matching icons only when they improve recognition.
- Password inputs should support visibility toggling.
- Provide validation feedback near the relevant field.

## States

- Every meaningful async action should communicate progress.
- Disable repeat submission while an action is in flight.
- Provide explicit empty states when lists or sections have no content.
- Show success and failure feedback in a consistent way.

## Error Presentation

- Use toasts for transient action feedback and network results that do not need field-level placement.
- Use inline errors for validation and field-specific problems.
- Keep all error text user-friendly and in Russian.
- Never surface raw backend messages directly.

## Accessibility

- All interactive controls need a descriptive accessible name.
- Keyboard navigation must work for menus, dialogs, dropdowns, and similar overlays.
- Focus states must remain visible.
- Maintain sufficient contrast in both light and dark themes.
- Touch targets should be comfortable on mobile.

## Theming

- Support both light and dark mode.
- Use semantic color roles consistently for primary actions, success, warning, danger, information, and neutral content.
- Keep visual emphasis aligned with action importance.

## Navigation and Safe Areas

- Mobile bottom navigation must not cover page content.
- Add enough bottom spacing for fixed mobile navigation when present.
- Keep primary actions reachable without conflicting with system gestures.

## Motion

- Use simple transitions to clarify state changes.
- Keep motion subtle and functional.
- Avoid heavy or decorative animation that competes with usability.

## Review Checklist

- The screen works on a narrow mobile viewport first.
- Flowbite-Svelte components are used where appropriate.
- All user-facing text is Russian.
- Loading, empty, success, and error states are present when needed.
- Light and dark themes remain usable.
- Keyboard access, focus visibility, and touch target size are acceptable.
