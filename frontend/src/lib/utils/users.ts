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
