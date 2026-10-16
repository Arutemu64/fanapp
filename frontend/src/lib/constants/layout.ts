/**
 * Where the sidebar replaces the bottom nav: Tailwind's `md`, pinned as
 * `--breakpoint-md` in app.css. JS behaviour tied to that swap (the top bar's
 * hide-on-scroll, the bottom scroll padding) matches on this query so it switches at
 * the same width as the `md:` classes. A media query can't read var(), so the value
 * lives in both files; layout.test.ts fails if they disagree.
 */
export const MD_BREAKPOINT = '48rem';

export const DESKTOP_MEDIA_QUERY = `(min-width: ${MD_BREAKPOINT})`;
