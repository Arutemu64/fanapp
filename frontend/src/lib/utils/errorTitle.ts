import { m } from '#lib/paraglide/messages.js';
/**
 * Short Russian title for an HTTP error status. Shared by ErrorState (the
 * on-screen heading) and +error.svelte (the document <title>) so the mapping
 * lives in one place. The offline case isn't tied to a status code and is
 * handled separately in ErrorState.
 */
export function statusTitle(status: number | undefined): string {
	if (status === 403) return m.error_title_forbidden();
	if (status === 404) return m.error_title_not_found();
	return m.error_title_generic();
}
