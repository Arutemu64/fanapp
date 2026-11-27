import type { Path } from '$app/types';
import type { Component } from 'svelte';

import type { CurrentUserDto } from '#lib/api/generated/index.js';

export interface BackTarget {
	href: Path;
	label: string;
}

export interface NavbarAction {
	href: Path;
	label: string;
	icon: Component;
	visibleFor?: (user: CurrentUserDto | null) => boolean;
}
