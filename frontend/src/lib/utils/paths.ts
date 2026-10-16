import type { Path, ResolvedPathname } from '$app/types';

import { resolve } from '$app/paths';

// `resolve` takes its argument as a union of one-element tuples, one per route.
// TypeScript relates a union argument (a `Path` held in a variable) to such a
// union only up to 25 members (`typeRelatedToDiscriminatedType`), and the app has
// more routes than that, so every non-literal call fails svelte-check. Each
// `Path` is a pathname with no params to fill, which is the one-argument call
// `resolve` makes for it, so this narrows the signature rather than bypass it.
// Literal paths keep calling `resolve` directly.
// TODO: drop this for plain `resolve` once SvelteKit's ResolveArgs stops
// distributing over every route — upstream has no issue for it yet.
export const resolvePath = resolve as (path: Path) => ResolvedPathname;
