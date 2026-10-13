import 'vue-router';

import type { PageData, RouteLoader, ShownError } from './load.js';

declare module 'vue-router' {
	interface RouteMeta {
		/** Runs before the navigation commits; see `RouteLoader`. */
		load?: RouteLoader;
		/** Set by the router once the loaders of the matched records have run. */
		pageData?: PageData;
		/** Set by the router when a loader failed; the shell renders it instead of the page. */
		error?: ShownError;
		/** The route needs a signed-in user (the group guard enforces it); true on every child. */
		protected?: boolean;
	}
}
