const roleLabels: Record<string, string> = {
	visitor: 'Посетитель',
	participant: 'Участник',
	helper: 'Волонтер',
	org: 'Организатор'
};

const roleColors: Record<string, 'gray' | 'blue' | 'green' | 'yellow'> = {
	visitor: 'gray',
	participant: 'blue',
	helper: 'green',
	org: 'yellow'
};

export function getRoleLabel(role: string): string {
	return roleLabels[role] || role;
}

export function getRoleColor(role: string): 'gray' | 'blue' | 'green' | 'yellow' {
	return roleColors[role] || 'gray';
}

// Build avatar initials from a username: two name parts -> two letters,
// otherwise the first two characters. Falls back to 'П' (Профиль) when blank.
export function getAvatarInitials(username: string | null | undefined): string {
	const name = username?.trim().replace(/^@/, '');

	if (!name) {
		return 'П';
	}

	const parts = name.split(/[\s._-]+/).filter(Boolean);

	if (parts.length >= 2) {
		const firstInitial = parts[0]?.[0] ?? '';
		const secondInitial = parts[1]?.[0] ?? '';

		return `${firstInitial}${secondInitial}`.toUpperCase();
	}

	return name.slice(0, 2).toUpperCase();
}
