/// <reference types="unplugin-icons/types/svelte" />

// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces

import type { UserFullDTO } from '$lib/types/user';

declare global {
	namespace App {
		interface Locals {
			user: UserFullDTO | null;
		}
		// interface Error {}
		interface PageData {
			user: UserFullDTO | null;
		}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
