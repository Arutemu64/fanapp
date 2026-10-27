import { m } from '#lib/paraglide/messages.js';
export function statusTitle(status: number | undefined): string {
	if (status === 403) return m.error_title_forbidden();
	if (status === 404) return m.error_title_not_found();
	return m.error_title_generic();
}
