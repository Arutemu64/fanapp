import { computed, type ComputedRef } from 'vue';
import { useRoute } from 'vue-router';

import type { PageData } from './load.js';

/**
 * The data the current route's loaders returned, merged parent → child. It is
 * stored on the route location itself, so it changes in the same tick as the
 * route and a page never renders with the next page's data.
 */
export function usePageData<T extends PageData = PageData>(): ComputedRef<T> {
	const route = useRoute();
	return computed(() => (route.meta.pageData ?? {}) as T);
}
