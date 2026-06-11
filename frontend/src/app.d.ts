/// <reference types="unplugin-icons/types/svelte" />

// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces

import type { UserFullDTO } from '$lib/types/user';

declare global {
	namespace App {
		interface Locals {
			user: UserFullDTO | null;
		}
		interface Error {
			message: string;
			code?: string;
		}
		interface PageData {
			user: UserFullDTO | null;
			/** Page heading rendered in the navbar; set per page via `load`. */
			title?: string;
		}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
