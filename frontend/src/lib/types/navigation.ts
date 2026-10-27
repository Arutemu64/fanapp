import type { Path } from '$app/types';
import type { Component } from 'svelte';

export interface BackTarget {
	href: Path;
	label: string;
}

export interface NavbarAction {
	href: Path;
	label: string;
	icon: Component;
}
