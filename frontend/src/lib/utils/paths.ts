import type { Path, ResolvedPathname } from '$app/types';

import { resolve } from '$app/paths';

export const resolvePath = resolve as (path: Path) => ResolvedPathname;
