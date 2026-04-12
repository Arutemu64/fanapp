import type { UserFullDTO } from '$lib/types/user';

export const roleLabels: Record<string, string> = {
	visitor: 'Посетитель',
	participant: 'Участник',
	helper: 'Волонтер',
	org: 'Организатор'
};

export const roleColors: Record<string, 'gray' | 'blue' | 'green' | 'yellow'> = {
	visitor: 'gray',
	participant: 'blue',
	helper: 'green',
	org: 'yellow'
};

export function getDisplayName(user: UserFullDTO): string {
	return user.first_name || user.username || 'Пользователь';
}

export function getRoleLabel(role: string): string {
	return roleLabels[role] || role;
}

export function getRoleColor(role: string): 'gray' | 'blue' | 'green' | 'yellow' {
	return roleColors[role] || 'gray';
}
