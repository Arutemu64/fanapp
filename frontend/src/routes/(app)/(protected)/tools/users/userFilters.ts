import type { UserRole } from '#lib/api/generated/index.js';

import { USER_ROLES } from '#lib/constants/users.js';

export interface UserFilters {
	search: string;
	role: UserRole | null;
	hasTicket: boolean | null;
}

// URL value of the ticket filter: short words rather than true/false, so a
// shared link reads as what it shows.
const TICKET_PARAM = { yes: true, no: false } as const;

function isUserRole(value: string | null): value is UserRole {
	return USER_ROLES.some((role) => role === value);
}

// The filters live in the URL so a filtered list survives the back button and
// can be shared. Anything unrecognised reads as "no filter" rather than an error:
// a hand-edited link should still open the list.
export function parseUserFilters(params: Pick<URLSearchParams, 'get'>): UserFilters {
	const role = params.get('role');
	const ticket = params.get('ticket');
	let hasTicket: boolean | null = null;
	if (ticket === 'yes' || ticket === 'no') {
		hasTicket = TICKET_PARAM[ticket];
	}
	return {
		search: params.get('q')?.trim() ?? '',
		role: isUserRole(role) ? role : null,
		hasTicket
	};
}

export function buildUserFiltersQuery(filters: UserFilters): string {
	const params = new URLSearchParams();
	const search = filters.search.trim();
	if (search) {
		params.set('q', search);
	}
	if (filters.role) {
		params.set('role', filters.role);
	}
	if (filters.hasTicket !== null) {
		params.set('ticket', filters.hasTicket ? 'yes' : 'no');
	}
	const query = params.toString();
	return query ? `?${query}` : '';
}
