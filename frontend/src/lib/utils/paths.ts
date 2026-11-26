import type { PathnameWithSearchOrHash, ResolvedPathname } from '$app/types';

import { resolve } from '$app/paths';

export const resolvePath = resolve as (path: PathnameWithSearchOrHash) => ResolvedPathname;
